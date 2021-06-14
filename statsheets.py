import blaseball_mike.database as mike
import sqlite3

def update():
    '''
    Updates sqlite3 database with this season's games to date
    '''

    print("Updating statsheets...")

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

    # Figure out which days to process. Always process today (obvious) and yesterday (in case of very long games, as this is run at fixed intervals)
    # mike uses 1-indexed seasons and days as input
    # blaseball.com returns 0-indexed seasons and days

    days_processed = [day[0] for day in sqldb.execute('''
        SELECT DISTINCT day FROM hitters_statsheets ORDER BY day
    ''')]
    today = sim['day']+1
    days = [day for day in range(1,today) if day not in days_processed] + [today-1, today] # Always this Day and Day-1, and everything else if needed

    # Get incinerated players. We'll skip these statsheets
    incinerated = mike.get_tributes()['players']
    incinerated_ids = [player['playerId'] for player in incinerated]

    # Get all player data
    for day in days:
        print("Processing Day {}...".format(day))
        # Get the day's game statsheets
        games = mike.get_games(season,day)
        game_ids = list(games.keys())
        game_statsheet_ids = [games[game_id]['statsheet'] for game_id in game_ids]
        game_statsheets = [mike.get_game_statsheets(game_statsheet_id)[game_statsheet_id] for game_statsheet_id in game_statsheet_ids]
        for game_statsheet in game_statsheets:
            # Get team statsheets
            teams = ['homeTeamStats', 'awayTeamStats']
            for team in teams:
                team_statsheet_id = game_statsheet[team]
                team_statsheet = mike.get_team_statsheets(team_statsheet_id)[team_statsheet_id]
                # Get player statsheets.
                player_statsheet_ids = team_statsheet['playerStats']
                player_statsheets = [mike.get_player_statsheets(player_statsheet_id)[player_statsheet_id] for player_statsheet_id in player_statsheet_ids]
                # Get only hitters, skip currently dead players, skip pitchers -> hitters in reverb, 
                hitter_statsheets = [statsheet for statsheet in player_statsheets if not any([statsheet['pitchesThrown'], statsheet['outsRecorded'], statsheet['walksIssued']]) and statsheet['playerId'] not in incinerated_ids]
                # When reverb swaps a hitter <-> pitcher, we still get the correct lineup size by ignoring the pitcher! (Whose stats should be ignored for the partial game anyway!)
                # Only count players that had a "PA" (AB+BB). This avoids counting attractors that peek out of the secret base (luckily it's very rare for a lineup player to only have sacrifice plays)
                hitter_statsheets = [statsheet for statsheet in hitter_statsheets if statsheet['walks'] or statsheet['atBats']]
                # Get lineup size. Count playerids instead of statsheets to account for scattered players who regained a letter this game
                # Feedbacked players only end up with a statsheet for their final team!! Yay!!
                hitter_ids = [statsheet['playerId'] for statsheet in hitter_statsheets]
                # minor TODO Ways lineup_size is still miscounted (too many statsheets): carcinization, ambush immediately following an inhabit
                # Get hitter stats
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
                    lineup_size = len(set(hitter_ids))

                    # If a player regains a letter, it creates two stat sheets. Merge them.
                    if player_id in hitters_stats:
                        oldlist = hitters_stats[player_id]
                        newlist = [statsheet_id, player_id, day, player_name, team_name, atbats+oldlist[5], pas+oldlist[6], hits+oldlist[7], homeruns+oldlist[8], steals+oldlist[9], lineup_size]
                        hitters_stats[player_id] = newlist
                    else:
                        hitters_stats[player_id] = [statsheet_id, player_id, day, player_name, team_name, atbats, pas, hits, homeruns, steals, lineup_size]
                for hitter_stats in hitters_stats.values():
                    # print(hitter_stats)
                    sqldb.execute('''INSERT INTO hitters_statsheets 
                        VALUES ("{0}", "{1}", {2}, "{3}", "{4}", {5}, {6}, {7}, {8}, {9}, {10})
                        ON CONFLICT (player_id, day) DO
                        UPDATE SET player_name="{3}", team_name="{4}", atbats={5}, pas={6}, hits={7}, homeruns={8}, steals={9}, lineup_size={10}'''.format(*hitter_stats)
                    )

    # Save this day's changes to database
    sqldb.commit()

    print("Statsheets updated.")

if __name__ == "__main__":
    update()