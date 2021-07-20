import blaseball_mike.database as mike
import gspread
import json
import logging
import sqlite3
from sseclient import SSEClient


def update(spreadsheet_ids):
    '''
    Updates all hitter stats in the future hitting income tab of this season's snack spreadsheet
    '''

    logging.info("Updating hitter spreadsheet...")

    # Get current season
    sim = mike.get_simulation_data()
    season = sim['season']+1
    spreadsheet_id = spreadsheet_ids[season]

    # Connect to spreadsheet
    credentials = gspread.service_account()
    worksheet = credentials.open_by_key(spreadsheet_id).worksheet('All Hitters')

    # Get current dates
    today = sim['day']+1
    tomorrow = sim['day']+2

    # Initialize database
    sqldb = sqlite3.connect('databases/blaseball_S{}.db'.format(season))
    sqldb.execute('''DROP TABLE IF EXISTS hitters_proj''')
    sqldb.execute('''
        CREATE TABLE IF NOT EXISTS hitters_proj (
            player_id TINYTEXT NOT NULL,
            player_name TINYTEXT,
            team_name TINYTEXT,
            games TINYINT UNSIGNED,
            pas SMALLINT UNSIGNED,
            hits SMALLINT UNSIGNED,
            homeruns SMALLINT UNSIGNED,
            steals SMALLINT UNSIGNED,
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
    # Mods that mean a player can't earn money
    inactive_mods = set(['ELSEWHERE','SHELLED','LEGENDARY','REPLICA','NON_IDOLIZED'])
    # Incinerated players
    incinerated = mike.get_tributes()['players']
    incinerated_ids = set([player['playerId'] for player in incinerated])
    # Map of team ID to shorthand
    teams = mike.get_all_teams()
    teams_shorten = {}
    for team_id in teams:
        teams_shorten[team_id] = teams[team_id]['shorthand']
    # List of teams in league (ignore historical/coffee cup teams)
    teams_inleague_ids = [team for team in teams if teams[team]['stadium']]
    teams_inleague = [team for team in teams.values() if team['stadium']]
    # Shadows players for players who moved to shadows
    shadows = [ids for team in teams_inleague for ids in team['shadows']]
    # Pitchers for players who reverbed/feedbacked to being a pitcher
    pitchers = [ids for team in teams_inleague for ids in team['rotation']]
    # Teams playing tomorrow to support the postseason
    teams_playing = set()
    # If it's preseason, we have no players to look at, so end
    if sim['phase'] in [1]:
        logging.info("It's preseason, so there aren't any hitters to look at!")
        return
    # If it's siesta, tomorrow is actually today!
    elif sim['phase'] in [3,5]:
        tomorrow_games = mike.get_games(season, today)
        for game in tomorrow_games:
            teams_playing.add(tomorrow_games[game]['awayTeam'])
            teams_playing.add(tomorrow_games[game]['homeTeam'])
    elif sim['phase'] in [8]:
        logging.info("Pre-Postseason detected. Getting streamData.")
        # Get full streamdata
        stream = SSEClient('http://blaseball.com/events/streamData')
        for message in stream:
            # At seemingly fixed intervals, the stream sends an empty message
            if not str(message):
                continue
            data = json.loads(str(message))
            # Sometimes the stream just sends fights
            if 'games' not in data['value']:
                continue
            # At this point, it's safe to process it
            games = json.loads(str(message))['value']['games']
            # ... Maybe
            brackets = games.get('postseasons')
            if not brackets:
                continue
            for bracket in brackets:
                matchups = bracket['allMatchups']
                for matchup in matchups:
                    if matchup['awayTeam'] and matchup['homeTeam']:
                        teams_playing.add(matchup['awayTeam'])
                        teams_playing.add(matchup['homeTeam'])
            break # Exit the loop now that we've got the necessary streamData
    # Otherwise, we can get games easily
    else:
        tomorrow_games = mike.get_games(season, tomorrow)
        for game in tomorrow_games:
            teams_playing.add(tomorrow_games[game]['awayTeam'])
            teams_playing.add(tomorrow_games[game]['homeTeam'])
    # After the election, get current team lineups to update the recommendations for D0
    if sim['phase'] == 0:
        teams_lineup = {}
        for team in teams_inleague:
            teammate_details = mike.get_player(team['lineup']).values()
            lineup_current = 0
            for teammate_detail in teammate_details:
                teammate_mods = set(teammate_detail['permAttr']+teammate_detail['seasAttr']+teammate_detail['itemAttr'])
                if not any(mod in teammate_mods for mod in ['SHELLED','ELSEWHERE']):
                    lineup_current += 1
            teams_lineup[team['id']] = lineup_current

    # Get players
    player_ids = sqldb.execute('''
        SELECT DISTINCT player_id FROM hitters_statsheets
    ''')

    # Get details for use later (mods, team active, etc.)
    player_ids = [player_id[0] for player_id in player_ids]
    player_details = mike.get_player(player_ids)
    # Only use players that belong to a team in the league. This will remove KLONGs who later became visible
    player_ids_inleague = [player_id for player_id in player_ids if player_id in player_details.keys() and player_details[player_id]['leagueTeamId'] in teams_inleague_ids]

    for player_id in player_ids_inleague:

        # If this player can't be gotten, like, say a ghost inhabits someone but the ghost doesn't technically EXIST...
        if player_id not in player_details:
            continue

        # Calculate money stats
        player_name = list(sqldb.execute('''
            SELECT player_name FROM hitters_statsheets WHERE player_id = "{}" ORDER by day DESC LIMIT 1
        '''.format(player_id)))[0][0]
        team_name = list(sqldb.execute('''
            SELECT team_name FROM hitters_statsheets WHERE player_id = "{}" ORDER by day DESC LIMIT 1
        '''.format(player_id)))[0][0]
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

        # if player_id == '11de4da3-8208-43ff-a1ff-0b3480a0fbf1':
        #     logging.info(pas/games)
        #     logging.info(lineup/games)
        #     logging.info(hits/pas)
        #     logging.info(homeruns/pas)
        #     logging.info(steals/pas)
        #     quit()
        # logging.info([player_name, atbats, pas, hits-homeruns, homeruns, steals])

        # Get current player mods
        player_mods = player_details[player_id]['permAttr']+player_details[player_id]['seasAttr']+player_details[player_id]['itemAttr']

        # Check if this player can earn any money next game
        # Check if this player has a mod preventing them from making money
        can_earn = int(not any(mod in player_mods for mod in inactive_mods))
        # Check if this player is currently in the shadows, pitching, or incinerated
        if player_id in shadows or player_id in pitchers or player_id in incinerated_ids:
            can_earn = 0
        # Check if this team is playing tomorrow
        # But if we're in the offseason still let them be shown to make D0 predictions for the next season
        if not player_details[player_id]['leagueTeamId'] in teams_playing and sim['phase'] not in [0,12,13]:
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

        # Calculate some other stats
        papg = pas/games
        lineup_avg = lineup/games

        # Get each player's current team's shortname (abbreviation)
        team_abbr = teams_shorten.get(player_details[player_id]['leagueTeamId'], 'NULL')

        # Finally, if we're between the election and D0, get updated lineup sizes post-election
        if sim['phase'] == 0:
            team_id = player_details[player_id]['leagueTeamId']
            if team_id in teams_inleague:
                lineup_current = teams_lineup[team_id]

        # Add player data to database
        entry = [player_id, player_name, team_abbr, games, pas, hits-homeruns, homeruns, steals, papg, hppa, hrppa, sbppa, lineup_avg, lineup_current, can_earn, multiplier]
        sqldb.execute('''INSERT INTO hitters_proj (player_id, player_name, team_name, games, pas, hits, homeruns, steals, papg, hppa, hrppa, sbppa, lineup_avg, lineup_current, can_earn, multiplier)
            VALUES ("{0}", "{1}", "{2}", {3}, {4}, {5}, {6}, {7}, {8}, {9}, {10}, {11}, {12}, {13}, {14}, {15})
            ON CONFLICT (player_id) DO
            UPDATE SET player_name="{1}", team_name="{2}", games={3}, pas={4}, hits={5}, homeruns={6}, steals={7}, papg={8}, hppa={9}, hrppa={10}, sbppa={11}, lineup_avg={12}, lineup_current={13}, can_earn={14}, multiplier={15}'''.format(*entry))

    # Save changes to database
    sqldb.commit()

    # Update spreadsheet
    payload = [list(player) for player in sqldb.execute('''SELECT * FROM hitters_proj ORDER BY team_name''')]
    while len(payload) < 350:
        payload.append(['','','','','','','','','','','','','','','',''])
    worksheet.update('A4:P', payload)

    # Update the day
    if sim['phase'] == 0: # After election, get full season projections!
        today = 0
    elif sim['phase'] in [3,5]: # For siestas, "today" actually hasn't happened yet
        today = today-1
    worksheet.update('B1', today)

    logging.info("Hitter spreadsheet updated.")

if __name__ == "__main__":
    spreadsheet_ids = {
        19: '1_p6jsPxMvO0nGE-fiqGfilu-dxeUc994k2zwAGNVNr0',
        20: '1EAqMvv2KrC9DjlJdlXrH_JXmHtAStxRJ661lWbuwYQs',
        21: '1DBCpsYlDOft5wve7IKTXAH-3zeoZIUy7A_R4a5uiYz8',
        22: '1nC8ZU0dz2kyOH4w78jIcitMdhk9KhVKbKBSXC1QEkXY',
        23: '1jAHAHGgjpZp_PGDyedEvSSJVY-7Sq9bVkMcMTZjSBtg',
        24: '12cbSlctxlukuUIxb9T9eo2lIcMmnEqvI7dkF9906a_Q'
    }
    update(spreadsheet_ids)
