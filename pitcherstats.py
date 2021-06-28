import blaseball_mike.database as mike
import gspread
import json
import logging
import sqlite3
from sseclient import SSEClient

def update(spreadsheet_ids):
    '''
    Updates all pitcher stats in the future hitting income tab of this season's snack spreadsheet
    '''

    logging.info("Updating pitcher spreadsheet...")

    # Get current season
    sim = mike.get_simulation_data()
    season = sim['season']+1
    spreadsheet_id = spreadsheet_ids[season]

    # Connect to spreadsheet
    credentials = gspread.service_account()
    worksheet = credentials.open_by_key(spreadsheet_id).worksheet('All Pitchers')

    # Get current dates
    today = sim['day']+1
    tomorrow = sim['day']+2

    # Initialize database
    sqldb = sqlite3.connect('databases/blaseball_S{}.db'.format(season))
    sqldb.execute('''DROP TABLE IF EXISTS pitchers_spreadsheet''')
    sqldb.execute('''
        CREATE TABLE IF NOT EXISTS pitchers_spreadsheet (
            player_id TINYTEXT NOT NULL,
            player_name TINYTEXT,
            team_name TINYTEXT,
            games TINYINT UNSIGNED,
            wins TINYINT UNSIGNED,
            losses TINYINT UNSIGNED,
            outs SMALLINT UNSIGNED,
            runs SMALLINT UNSIGNED,
            strikeouts SMALLINT UNSIGNED,
            homeruns SMALLINT UNSIGNED,
            shutouts TINYINT UNSIGNED,
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
    # Map of team full name to shorthand
    teams = mike.get_all_teams()
    teams_shorten = {}
    for team_id in teams:
        teams_shorten[team_id] = teams[team_id]['shorthand']
    # List of teams in league (ignore historical/coffee cup teams)
    teams_inleague = [team for team in teams.values() if team['stadium']]
    # Shadows players for players who moved to shadows
    shadows = [ids for team in teams_inleague for ids in team['shadows']]
    # Hitters for players who reverbed/feedbacked to being a pitcher
    hitters = [ids for team in teams_inleague for ids in team['lineup']]
    # Teams playing tomorrow to support the postseason
    teams_playing = set()
    # After the brackets have been decided but before the first round begins, it's complicated
    if sim['phase'] in [8]:
        logging.info("Pre-Postseason detected. Getting streamData.")
        # Get full streamdata
        stream = SSEClient('http://blaseball.com/events/streamData')
        for message in stream:
            # At seemingly fixed intervals, the stream sends an empty message
            if not str(message):
                moveon += 1
                continue
            data = json.loads(str(message))
            # Sometimes the stream just sends fights
            if 'games' not in data['value']:
                moveon += 1
                continue
            # At this point, it's safe to process it
            games = json.loads(str(message))['value']['games']
            brackets = games.get('postseasons')
            # ... Maybe
            if not brackets:
                continue
            for bracket in brackets:
                matchups = bracket['allMatchups']
                for matchup in matchups:
                    if matchup['awayTeam'] and matchup['homeTeam']:
                        teams_playing.add(matchup['awayTeam'])
                        teams_playing.add(matchup['homeTeam'])
            break
    else:
        tomorrow_games = mike.get_games(season, tomorrow)
        for game in tomorrow_games:
            teams_playing.add(tomorrow_games[game]['awayTeam'])
            teams_playing.add(tomorrow_games[game]['homeTeam'])

    # Get pitchers
    player_ids = sqldb.execute('''
        SELECT DISTINCT player_id FROM pitchers_statsheets
    ''')

    # Get details for use later (mods, team active, etc.)
    player_ids = [player_id[0] for player_id in player_ids]
    player_details = mike.get_player(player_ids)

    for player_id in player_ids:

        # If this player can't be gotten, like, say a ghost inhabits someone but the ghost doesn't technically EXIST...
        if player_id not in player_details:
            continue

        # Calculate money stats
        player_name = list(sqldb.execute('''
            SELECT player_name FROM pitchers_statsheets WHERE player_id = "{}" ORDER by day DESC LIMIT 1
        '''.format(player_id)))[0][0]
        team_name = list(sqldb.execute('''
            SELECT team_name FROM pitchers_statsheets WHERE player_id = "{}" ORDER by day DESC LIMIT 1
        '''.format(player_id)))[0][0]
        games = list(sqldb.execute('''
            SELECT Count(*) FROM pitchers_statsheets WHERE player_id = "{}"
        '''.format(player_id)))[0][0]
        wins = list(sqldb.execute('''
            SELECT SUM(wins) FROM pitchers_statsheets WHERE player_id = "{}"
        '''.format(player_id)))[0][0]
        losses = list(sqldb.execute('''
            SELECT SUM(losses) FROM pitchers_statsheets WHERE player_id = "{}"
        '''.format(player_id)))[0][0]
        outs = list(sqldb.execute('''
            SELECT SUM(outs) FROM pitchers_statsheets WHERE player_id = "{}"
        '''.format(player_id)))[0][0]
        runs = list(sqldb.execute('''
            SELECT SUM(runs) FROM pitchers_statsheets WHERE player_id = "{}"
        '''.format(player_id)))[0][0]
        strikeouts = list(sqldb.execute('''
            SELECT SUM(strikeouts) FROM pitchers_statsheets WHERE player_id = "{}"
        '''.format(player_id)))[0][0]
        homeruns = list(sqldb.execute('''
            SELECT SUM(homeruns) FROM pitchers_statsheets WHERE player_id = "{}"
        '''.format(player_id)))[0][0]
        shutouts = list(sqldb.execute('''
            SELECT SUM(shutouts) FROM pitchers_statsheets WHERE player_id = "{}"
        '''.format(player_id)))[0][0]

        # Get current player mods
        player_mods = player_details[player_id]['permAttr']+player_details[player_id]['seasAttr']+player_details[player_id]['itemAttr']

        # Check if this player can earn any money next game
        # Check if this player has a mod preventing them from making money
        can_earn = int(not any(mod in player_mods for mod in inactive_mods))
        # Check if this player is currently in the shadows, hitting, or incinerated
        if player_id in shadows or player_id in hitters or player_id in incinerated_ids:
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

        # Get each player's current team's shortname (abbreviation)
        team_abbr = teams_shorten.get(player_details[player_id]['leagueTeamId'], 'NULL')

        # Add player data to database
        entry = [player_id, player_name, team_abbr, games, wins, losses, outs, runs, strikeouts, homeruns, shutouts, can_earn, multiplier]
        sqldb.execute('''INSERT INTO pitchers_spreadsheet (player_id, player_name, team_name, games, wins, losses, outs, runs, strikeouts, homeruns, shutouts, can_earn, multiplier)
            VALUES ("{0}", "{1}", "{2}", {3}, {4}, {5}, {6}, {7}, {8}, {9}, {10}, {11}, {12})
            ON CONFLICT (player_id) DO
            UPDATE SET player_name="{1}", team_name="{2}", games={3}, wins={4}, losses={5}, outs={6}, runs={7}, strikeouts={8}, homeruns={9}, shutouts={10}, can_earn={11}, multiplier={12}'''.format(*entry))

    # Save changes to database
    sqldb.commit()

    # Update spreadsheet
    payload = [list(player) for player in sqldb.execute('''SELECT * FROM pitchers_spreadsheet ORDER BY team_name''')]
    while len(payload) < 125:
        payload.append(['','','','','','','','','','','','',''])
    worksheet.update('A4:P', payload)

    # Update the day
    worksheet.update('B1', today)

    logging.info("Pitcher spreadsheet updated.")

if __name__ == "__main__":
    spreadsheet_ids = {
        19: '1_p6jsPxMvO0nGE-fiqGfilu-dxeUc994k2zwAGNVNr0',
        20: '1EAqMvv2KrC9DjlJdlXrH_JXmHtAStxRJ661lWbuwYQs',
        21: '1DBCpsYlDOft5wve7IKTXAH-3zeoZIUy7A_R4a5uiYz8',
        22: '1nC8ZU0dz2kyOH4w78jIcitMdhk9KhVKbKBSXC1QEkXY'
    }
    update(spreadsheet_ids)