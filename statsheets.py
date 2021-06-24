import blaseball_mike.database as mike
import logging
import sqlite3

def update():
    '''
    Updates sqlite3 database with this season's games to date
    '''

    logging.info("Updating statsheets...")

    # Get season
    sim = mike.get_simulation_data()
    season = sim['season']+1

    # Initialize database
    sqldb = sqlite3.connect('databases/blaseball_S{}.db'.format(season))
    sqldb.execute('''
        CREATE TABLE IF NOT EXISTS hitters_statsheets (
            statsheet_id TINYTEXT,
            player_id TINYTEXT NOT NULL,
            day TINYINT UNSIGNED,
            player_name TINYTEXT,
            team_name TINYTEXT,
            atbats SMALLINT UNSIGNED,
            pas SMALLINT UNSIGNED,
            hits SMALLINT UNSIGNED,
            homeruns SMALLINT UNSIGNED,
            steals SMALLINT UNSIGNED,
            lineup_size TINYINT UNSIGNED,
            primary key (player_id, day)
        )
    ''')
    sqldb.execute('''
        CREATE TABLE IF NOT EXISTS pitchers_statsheets (
            statsheet_id TINYTEXT,
            player_id TINYTEXT NOT NULL,
            day TINYINT UNSIGNED,
            player_name TINYTEXT,
            team_name TINYTEXT,
            wins TINYINT UNSIGNED,
            losses TINYINT UNSIGNED,
            outs SMALLINT UNSIGNED,
            runs SMALLINT UNSIGNED,
            strikeouts SMALLINT UNSIGNED,
            homeruns SMALLINT UNSIGNED,
            shutouts TINYINT UNSIGNED,
            primary key (player_id, day)
        )
    ''')

    # Figure out which days to process. Always process today (obvious) and yesterday (in case of very long games, as this is run at fixed intervals)
    # mike uses 1-indexed seasons and days as input
    # blaseball.com returns 0-indexed seasons and days

    days_processed = set([day[0] for day in sqldb.execute('''
        SELECT DISTINCT day FROM hitters_statsheets ORDER BY day
    ''')])
    today = sim['day']+1
    days = [day for day in range(1,today) if day not in days_processed] + [today] # Always today, and everything else if needed

    # Get incinerated players. We'll skip these statsheets
    incinerated = mike.get_tributes()['players']
    incinerated_ids = set([player['playerId'] for player in incinerated])

    # Get all player data
    for day in days:
        logging.info("Processing Day {}...".format(day))
        # Get the day's game statsheets
        games = mike.get_games(season,day)
        game_ids = list(games.keys())
        game_statsheet_ids = [games[game_id]['statsheet'] for game_id in game_ids]
        game_statsheets = mike.get_game_statsheets(game_statsheet_ids).values()
        # Get team statsheets
        teams = ['homeTeamStats', 'awayTeamStats']
        team_statsheet_ids_pairs = [(game_statsheet['homeTeamStats'],game_statsheet['awayTeamStats']) for game_statsheet in game_statsheets]
        team_statsheet_ids = [game_statsheet[team] for game_statsheet in game_statsheets for team in teams]
        team_statsheets = mike.get_team_statsheets(team_statsheet_ids)
        # Get player statsheets
        for team_statsheet_ids_pair in team_statsheet_ids_pairs:
            team_statsheet_home = team_statsheets[team_statsheet_ids_pair[0]]
            team_statsheet_away = team_statsheets[team_statsheet_ids_pair[1]]
            player_statsheet_ids_home = team_statsheet_home['playerStats']
            player_statsheet_ids_away = team_statsheet_away['playerStats']
            player_statsheets_home = mike.get_player_statsheets(player_statsheet_ids_home).values()
            player_statsheets_away = mike.get_player_statsheets(player_statsheet_ids_away).values()
            pitcher_statsheets_teams = {}
            pitcher_statsheets_teams['home'] = [statsheet for statsheet in player_statsheets_home if any([statsheet['outsRecorded'], statsheet['walksIssued']])]
            pitcher_statsheets_teams['away'] = [statsheet for statsheet in player_statsheets_away if any([statsheet['outsRecorded'], statsheet['walksIssued']])]
            # Get only hitters. Also skips pitchers -> hitters in reverb, but it's a small price to pay
            hitter_statsheets_home = [statsheet for statsheet in player_statsheets_home if not any([statsheet['pitchesThrown'], statsheet['outsRecorded'], statsheet['walksIssued']])]
            hitter_statsheets_away = [statsheet for statsheet in player_statsheets_away if not any([statsheet['pitchesThrown'], statsheet['outsRecorded'], statsheet['walksIssued']])]
            # Determine homeruns given up by pitchers before we filter out other people
            homeruns_allowed = {}
            homeruns_allowed['away'] = sum([statsheet['homeRuns'] for statsheet in hitter_statsheets_home])
            homeruns_allowed['home'] = sum([statsheet['homeRuns'] for statsheet in hitter_statsheets_away])
            # When reverb swaps a hitter <-> pitcher, we still get the correct lineup size by ignoring the pitcher! (Whose stats should be ignored for the partial game anyway!)
            # Only count players that had a "PA" (AB+BB). This avoids counting attractors that peek out of the secret base (luckily it's very rare for a lineup player to only have sacrifice plays)
            hitter_statsheets_home = [statsheet for statsheet in hitter_statsheets_home if statsheet['walks'] or statsheet['atBats']]
            hitter_statsheets_away = [statsheet for statsheet in hitter_statsheets_away if statsheet['walks'] or statsheet['atBats']]
            # Skip currently dead players. This purely to avoid ghosts. Bad news is we don't count players incinerated this game for lineup size
            hitter_statsheets_home = [statsheet for statsheet in hitter_statsheets_home if statsheet['playerId'] not in incinerated_ids]
            hitter_statsheets_away = [statsheet for statsheet in hitter_statsheets_away if statsheet['playerId'] not in incinerated_ids]

            # Assemble pitcher stats
            pitchers_stats = {}
            for team in pitcher_statsheets_teams:
                for pitcher_statsheet in pitcher_statsheets_teams[team]:
                    # Easy stats
                    statsheet_id = pitcher_statsheet['id']
                    player_id = pitcher_statsheet['playerId']
                    player_name = pitcher_statsheet['name']
                    team_name = pitcher_statsheet['team']
                    outs = pitcher_statsheet['outsRecorded']
                    runs = pitcher_statsheet['earnedRuns']
                    wins = pitcher_statsheet['wins']
                    losses = pitcher_statsheet['losses']
                    strikeouts = pitcher_statsheet['strikeouts']
                    # Homeruns aren't split by pitcher, so let's just split them evenly between all pitchers
                    homeruns = homeruns_allowed[team]/len(pitcher_statsheets_teams[team])
                    # This shutout definition is very likely wrong, but it's what we have for now
                    shutouts = 1 if outs >= 24 and runs == 0 else 0
                    # If a player regains a letter, it creates two stat sheets. Merge them. For pitchers, this should basically never happen
                    if player_id in pitchers_stats:
                        oldlist = pitchers_stats[player_id]
                        shutouts = 1 if outs+oldlist[7] >= 24 and runs+oldlist[8] == 0 else 0
                        newlist = [statsheet_id, player_id, day, player_name, team_name, wins+oldlist[5], losses+oldlist[6], outs+oldlist[7], runs+oldlist[8], strikeouts+oldlist[9], homeruns+oldlist[10], shutouts]
                        pitchers_stats[player_id] = newlist
                    else:
                        pitchers_stats[player_id] = [statsheet_id, player_id, day, player_name, team_name, wins, losses, outs, runs, strikeouts, homeruns, shutouts]
            for pitcher_stats in pitchers_stats.values():
                sqldb.execute('''INSERT INTO pitchers_statsheets (statsheet_id, player_id, day, player_name, team_name, wins, losses, outs, runs, strikeouts, homeruns, shutouts)
                    VALUES ("{0}", "{1}", {2}, "{3}", "{4}", {5}, {6}, {7}, {8}, {9}, {10}, {11})
                    ON CONFLICT (player_id, day) DO
                    UPDATE SET player_name="{3}", team_name="{4}", wins={5}, losses={6}, outs={7}, runs={8}, strikeouts={9}, homeruns={10}, shutouts={11}'''.format(*pitcher_stats)
                )
                
            # Assemble hitter stats
            for hitter_statsheets in [hitter_statsheets_home, hitter_statsheets_away]:
                # Get this team's lineup size for today
                lineup_size = len(hitter_statsheets)
                # For the Crabs, Ignore KLONGs (Kennedy Loser Nonexistent Ghosts/New Guys). These ghosts are incinerated but won't show up as such.
                if hitter_statsheets[0]['team'] == 'Baltimore Crabs':
                    hitter_ids = [statsheet['playerId'] for statsheet in hitter_statsheets]
                    lineup_size = len(mike.get_player(hitter_ids).keys())
                hitters_stats = {}
                for hitter_statsheet in hitter_statsheets:
                    # Easy stats
                    statsheet_id = hitter_statsheet['id']
                    player_id = hitter_statsheet['playerId']
                    player_name = hitter_statsheet['name']
                    team_name = hitter_statsheet['team']
                    atbats = hitter_statsheet['atBats']
                    pas = atbats+hitter_statsheet['walks']
                    hits = hitter_statsheet['hits']
                    homeruns = hitter_statsheet['homeRuns']
                    steals = hitter_statsheet['stolenBases']

                    # If a player regains a letter, it creates two stat sheets. Merge them.
                    if player_id in hitters_stats:
                        oldlist = hitters_stats[player_id]
                        newlist = [statsheet_id, player_id, day, player_name, team_name, atbats+oldlist[5], pas+oldlist[6], hits+oldlist[7], homeruns+oldlist[8], steals+oldlist[9], lineup_size]
                        hitters_stats[player_id] = newlist
                    else:
                        hitters_stats[player_id] = [statsheet_id, player_id, day, player_name, team_name, atbats, pas, hits, homeruns, steals, lineup_size]
                for hitter_stats in hitters_stats.values():
                    sqldb.execute('''INSERT INTO hitters_statsheets (statsheet_id, player_id, day, player_name, team_name, atbats, pas, hits, homeruns, steals, lineup_size)
                        VALUES ("{0}", "{1}", {2}, "{3}", "{4}", {5}, {6}, {7}, {8}, {9}, {10})
                        ON CONFLICT (player_id, day) DO
                        UPDATE SET player_name="{3}", team_name="{4}", atbats={5}, pas={6}, hits={7}, homeruns={8}, steals={9}, lineup_size={10}'''.format(*hitter_stats)
                    )

        # Save this day's changes to database
        sqldb.commit()

    logging.info("Statsheets updated.")

if __name__ == "__main__":
    update()
