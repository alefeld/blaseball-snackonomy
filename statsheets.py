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
            statsheet_id TEXT,
            player_id TEXT NOT NULL,
            day INTEGER,
            player_name TEXT,
            team_name TEXT,
            atbats INTEGER,
            pas INTEGER,
            hits INTEGER,
            homeruns INTEGER,
            steals INTEGER,
            lineup_size INTEGER,
            primary key (player_id, day)
        )
    ''')
    sqldb.execute('''
        CREATE TABLE IF NOT EXISTS pitchers_statsheets (
            statsheet_id TEXT,
            player_id TEXT NOT NULL,
            day INTEGER,
            player_name TEXT,
            team_name TEXT,
            wins INTEGER,
            losses INTEGER,
            outs INTEGER,
            runs INTEGER,
            strikeouts INTEGER,
            homeruns INTEGER,
            shutouts INTEGER,
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
    # If it's preseason, we have nothing to process, so end.
    if sim['phase'] in [1]:
        logging.info("It's preseason, so there aren't any statsheets to process!")
        return
    # If we're in siesta, don't process "today" because "today" is actually tomorrow
    if sim['phase'] in [3,5]:
        days.remove(today)

    # Get incinerated players. We'll skip these statsheets
    incinerated = mike.get_tributes()['players']
    incinerated_ids = set([player['playerId'] for player in incinerated])
    # Get teams with haunted lineups. Use this to exclude KLONGs from lineup size later
    teams_haunted = set()
    teams_all = mike.get_all_teams()
    newteams = ['b47df036-3aa4-4b98-8e9e-fe1d3ff1894b','2e22beba-8e36-42ba-a8bf-975683c52b5f']
    teams_inleague = [team for team in teams_all.values() if team['stadium'] and team['id'] != '698cfc6d-e95e-4391-b754-b87337e4d2a9' or team['id'] in newteams]
    hitters_inleague_ids = []
    for team_inleague in teams_inleague:
        hitters_inleague_ids.extend(team_inleague['lineup'])
    hitters_inleague = mike.get_player(hitters_inleague_ids)
    for hitter in hitters_inleague.values():
        if 'HAUNTED' in hitter['permAttr']:
            teams_haunted.add(hitter['leagueTeamId'])

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
                # Calculate lineup size. If this team is haunted, do this carefully (takes longer).
                if hitter_statsheets[0]['teamId'] in teams_haunted:
                    hitter_ids = [statsheet['playerId'] for statsheet in hitter_statsheets]
                    lineup_size = len(mike.get_player(hitter_ids).keys())
                else:
                    lineup_size = len(set([hitter_statsheet['playerId'] for hitter_statsheet in hitter_statsheets]))
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
