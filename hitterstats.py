import gspread
import blaseball_mike.database as bb
import sqlite3

def update(spreadsheet_id):
    print("Updating hitter spreadsheet...")

    # Connect to spreadsheet
    credentials = gspread.service_account()
    worksheet = credentials.open_by_key(spreadsheet_id).worksheet('Hitting Future Income')

    # Get season
    sim = bb.get_simulation_data()
    season = sim['season']+1
    today = sim['day']+1
    tomorrow = today+1

    # Initialize database
    sqldb = sqlite3.connect('blaseball_S{}.db'.format(season))
    sqldb.execute('''DROP TABLE IF EXISTS hitters_proj''')
    sqldb.execute('''
        CREATE TABLE IF NOT EXISTS hitters_proj (
            player_id TINYTEXT NOT NULL,
            player_name TINYTEXT,
            team_name TINYTEXT,
            games TINYINT UNSIGNED,
            papg FLOAT,
            hppa FLOAT,
            hrppa FLOAT,
            sbppa FLOAT,
            lineup_avg FLOAT,
            lineup_current TINYINT UNSIGNED,
            can_earn TINYINT UNSIGNED,
            multiplier TINYINT UNSIGNED,
            primary key (player_id)
        )
    ''')

    # Prep some fields:
    inactive_mods = ['ELSEWHERE','SHELLED','LEGENDARY','REPLICA','NON_IDOLIZED']
    teams = bb.get_all_teams()
    teams_shorten = {}
    for team in teams:
        teams_shorten[teams[team]['fullName']] = teams[team]['shorthand']
    bench = [ids for team in teams.values() for ids in team['bench'] if team['stadium']]
    bullpen = [ids for team in teams.values() for ids in team['bullpen'] if team['stadium']]
    shadows = bench+bullpen

    # Get players
    player_ids = sqldb.execute('''
        SELECT DISTINCT player_id FROM hitters_statsheets
    ''')

    for player_id in player_ids:
        player_id = player_id[0]

        # Calculate money stats
        games = list(sqldb.execute('''
            SELECT Count(*) FROM hitters_statsheets WHERE player_id = "{}"
        '''.format(player_id)))[0][0]
        pas = list(sqldb.execute('''
            SELECT SUM(pas) FROM hitters_statsheets WHERE player_id = "{}"
        '''.format(player_id)))[0][0]
        hits = list(sqldb.execute('''
            SELECT SUM(hits) FROM hitters_statsheets WHERE player_id = "{}"
        '''.format(player_id)))[0][0]
        homeruns = list(sqldb.execute('''
            SELECT SUM(homeruns) FROM hitters_statsheets WHERE player_id = "{}"
        '''.format(player_id)))[0][0]
        steals = list(sqldb.execute('''
            SELECT SUM(steals) FROM hitters_statsheets WHERE player_id = "{}"
        '''.format(player_id)))[0][0]
        lineup = list(sqldb.execute('''
            SELECT SUM(lineup_size) FROM hitters_statsheets WHERE player_id = "{}"
        '''.format(player_id)))[0][0]
        lineup_current = list(sqldb.execute('''
            SELECT lineup_size FROM hitters_statsheets WHERE player_id = "{}" ORDER by day DESC LIMIT 1
        '''.format(player_id)))[0][0]
        player_name = list(sqldb.execute('''
            SELECT player_name FROM hitters_statsheets WHERE player_id = "{}" ORDER by day DESC LIMIT 1
        '''.format(player_id)))[0][0]
        team_name = list(sqldb.execute('''
            SELECT team_name FROM hitters_statsheets WHERE player_id = "{}" ORDER by day DESC LIMIT 1
        '''.format(player_id)))[0][0]

        # if player_id == '11de4da3-8208-43ff-a1ff-0b3480a0fbf1':
        #     print(pas/games)
        #     print(lineup/games)
        #     print(hits/pas)
        #     print(homeruns/pas)
        #     print(steals/pas)
        #     quit()
        # print([player_name, atbats, pas, hits-homeruns, homeruns, steals])

        # Get current player mods
        player_detail = bb.get_player(player_id)[player_id]
        # print(player_detail)
        # quit()
        player_mods = player_detail['permAttr']+player_detail['seasAttr']+player_detail['itemAttr']

        # Check if this player can earn any money next game
        # Check if this player has a mod preventing them from making money
        can_earn = int(not any(mod in player_mods for mod in inactive_mods))
        # Check if this player is currently in the shadows
        if player_id in shadows:
            can_earn = 0
        # Check if this team is playing tomorrow
        tomorrow_games = bb.get_games(season, tomorrow)
        teams_playing = []
        for game in tomorrow_games:
            teams_playing.append(tomorrow_games[game]['awayTeam'])
            teams_playing.append(tomorrow_games[game]['homeTeam'])
        # But if we're in the offseason still let them be shown to make D0 predictions for the next season
        if not player_detail['leagueTeamId'] in teams_playing and sim['phase'] not in [0,13]:
            can_earn = 0

        # Determine payout multiplier
        multiplier = 1
        if 'DOUBLE_PAYOUTS' in player_mods:
            multiplier = 2
        if 'CREDIT_TO_THE_TEAM' in player_mods:
            multiplier = 5

        # Get earning stats
        hppa = (hits-homeruns)/pas # Homeruns don't count for seeds
        hrppa = homeruns/pas
        sbppa = steals/pas

        # Calculate come other stats
        papg = pas/games
        lineup_avg = lineup/games

        # Finally, if we're between the election and D0, get updated teams and lineup sizes post-election
        if sim['phase'] == 0:
            team_id = player_detail['leagueTeamId']
            team_detail = bb.get_team(team_id)
            team_name = team_detail['fullName']
            teammate_ids = team_detail['lineup']
            lineup_current = 0
            for teammate_id in teammate_ids:
                teammate_detail = bb.get_player(teammate_id)[teammate_id]
                teammate_mods = teammate_detail['permAttr']+teammate_detail['seasAttr']+teammate_detail['itemAttr']
                if not any(mod in teammate_mods for mod in ['SHELLED','ELSEWHERE']):
                    lineup_current += 1

        entry = [player_id, player_name, teams_shorten[team_name], games, papg, hppa, hrppa, sbppa, lineup_avg, lineup_current, can_earn, multiplier]
        sqldb.execute('''INSERT INTO hitters_proj 
            VALUES ("{0}", "{1}", "{2}", {3}, {4}, {5}, {6}, {7}, {8}, {9}, {10}, {11})
            ON CONFLICT (player_id) DO
            UPDATE SET player_name="{1}", team_name="{2}", games={3}, papg={4}, hppa={5}, hrppa={6}, sbppa={7}, lineup_avg={8}, lineup_current={9}, can_earn={10}, multiplier={11}'''.format(*entry))

    # Save changes to database
    sqldb.commit()

    # Update spreadsheet
    payload = [list(player) for player in sqldb.execute('''SELECT * FROM hitters_proj ORDER BY team_name''')]
    while len(payload) < 291:
        payload.append(['','','','','','','','','','','',''])
    worksheet.update('A39:L', payload)

    # Update the day
    worksheet.update('A37', today)

    print("Hitter spreadsheet updated.")

if __name__ == "__main__":
    update('1_p6jsPxMvO0nGE-fiqGfilu-dxeUc994k2zwAGNVNr0')