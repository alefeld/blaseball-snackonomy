import blaseball_mike.database as mike
import gspread
import itertools
import json
import logging
import requests
from sseclient import SSEClient

''' phases
            e[e.Preseason = 1] = "Preseason",
            e[e.Earlseason = 2] = "Earlseason",
            e[e.EarlySiesta = 3] = "EarlySiesta",
            e[e.Midseason = 4] = "Midseason",
            e[e.LateSiesta = 5] = "LateSiesta",
            e[e.Lateseason = 6] = "Lateseason",
            e[e.SeasonEnd = 7] = "SeasonEnd",
            e[e.PrePostseason = 8] = "PrePostseason",
            e[e.EarlyPostseason = 9] = "EarlyPostseason",
            e[e.EarlyPostseasonEnd = 10] = "EarlyPostseasonEnd",
            e[e.Postseason = 11] = "Postseason",
            e[e.PostseasonEnd = 12] = "PostseasonEnd",
            e[e.Election = 13] = "Election"
'''

def update(spreadsheet_ids):
    '''
    Updates tomorrow's pitchers in this season's snack spreadsheet
    '''

    logging.info("Updating tomorrow's pitchers...")

    # Get current season
    sim = mike.get_simulation_data()
    season = sim['season']+1
    spreadsheet_id = spreadsheet_ids[season]

    # Connect to spreadsheet
    credentials = gspread.service_account()
    worksheet = credentials.open_by_key(spreadsheet_id).worksheet('Tomorrow\'s Pitchers')

    # Map of team ID to shorthand
    teams = mike.get_all_teams()
    teams_shorten = {}
    for team_id in teams:
        teams_shorten[team_id] = teams[team_id]['shorthand']

    # Get Tomorrow
    # Preseason, Earlsiesta, and Latesiesta mess up the "tomorrow" thing since the day starts before games do
    if sim['phase'] in [1,3,5]:
        tomorrow = sim['day']+1
    # After the brackets have been decided but before the wildcard round begins, it's really complicated
    # Get Day 99 pitchers and the matchups for Day 100
    elif sim['phase'] in [8]:
        tomorrow = 100
        logging.info("Pre-Postseason detected. Getting streamData.")
        matchups_d100 = {}
        pitchers_d99 = {}
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
            brackets = games.get('postseasons')
            # ... Maybe. Let's be really sure
            if not brackets:
                continue
            # Get D100 teams
            for bracket in brackets:
                matchups = bracket['allMatchups']
                for matchup in matchups:
                    if matchup['awayTeam'] and matchup['homeTeam']: # Only get wildcard matchups
                        matchups_d100[matchup['id']] = {
                            'awayTeam': matchup['awayTeam'],
                            'homeTeam': matchup['homeTeam']
                        }
            # Get D99 pitchers to calculate D100 pitchers later
            for game in games['schedule']:
                pitchers_d99[game['awayTeam']] = game['awayPitcher']
                pitchers_d99[game['homeTeam']] = game['homePitcher']
            break # Exit the loop now that we've got the necessary streamData
    # If it's just a normal part of the season or postseason after D100, it's super easy
    else:
        # Check if today's games are finished. Tomorrow's pitchers could be wrong, otherwise.
        today = sim['day']+1
        games_today = mike.get_games(season, today).values()
        complete = [game['gameComplete'] for game in games_today]
        if not all(complete):
            logging.info("Games not complete. Tomorrow's pitchers might be wrong, so waiting...")
            return
        tomorrow = sim['day']+2

    # Get tomorrow's game
    # mike uses 1-indexed seasons and days as input
    # blaseball.com returns 0-indexed seasons and days
    # If we're preseason, we need to manually get Day 1 pitchers (first in lineup)
    if sim['phase'] in [1]:
        # Get all teams playing
        games = mike.get_games(season, tomorrow)
        for game_id in games:
            team_home_id = games[game_id]['homeTeam']
            team_home = mike.get_team(team_home_id)
            pitcher_home_id = team_home['rotation'][0]
            pitcher_home = mike.get_player(pitcher_home_id)
            pitcher_home_name = list(pitcher_home.values())[0]['name']
            games[game_id]['homeTeam'] = team_home_id
            games[game_id]['homeOdds'] = 0.500
            games[game_id]['homePitcher'] = pitcher_home_id
            games[game_id]['homePitcherName'] = pitcher_home_name
            team_away_id = games[game_id]['awayTeam']
            team_away = mike.get_team(team_away_id)
            pitcher_away_id = team_away['rotation'][0]
            pitcher_away = mike.get_player(pitcher_away_id)
            pitcher_away_name = list(pitcher_away.values())[0]['name']
            games[game_id]['awayTeam'] = team_away_id
            games[game_id]['awayOdds'] = 0.500
            games[game_id]['awayPitcher'] = pitcher_away_id
            games[game_id]['awayPitcherName'] = pitcher_away_name
    # If pre-playoffs, we have to be more creative.
    elif sim['phase'] in [8]:
        # Get wildcard round team details
        team_ids = []
        for matchup in matchups_d100.values():
            team_ids.append(matchup['awayTeam'])
            team_ids.append(matchup['homeTeam'])
        teams_d100 = {}
        for team_id in team_ids:
            team = mike.get_team(team_id)
            teams_d100[team['id']] = team
        
        # Iterate over the playoffs matchups to get D100 pitchers
        games = {}
        inactive_mods = ['ELSEWHERE','SHELLED']
        for idx,matchup in enumerate(matchups_d100.values()):
            games[idx] = {'weather': 0}
            for team_side in ['homeTeam','awayTeam']:
                # Get the ID of the D100 home pitcher. Start by finding slot that pitched D99
                team_id = matchup[team_side]
                rotation = teams_d100[team_id]['rotation']*4
                pitcher_d99 = pitchers_d99[team_id]
                # Get enough games prior to D99 to cover every pitcher slot
                games_before_num = [98-n for n in range(len(teams_d100[team_id]['rotation'])-1)]
                games_sets_before_all = [list(mike.get_games(season, game).values()) for game in games_before_num]
                games_before_team = []
                for games_set_before_all in games_sets_before_all:
                    game_before_team = [game for game in games_set_before_all if team_id in game['homeTeam'] or team_id in game['awayTeam']][0]
                    games_before_team.append(game_before_team)
                # Loop through those prior games to determine the D99 pitching slot
                slot_99_idx = 0 # Need a default in case there's only one active pitcher.
                for game_idx,game in enumerate(games_before_team):
                    if game['homeTeam'] == team_id:
                        pitcher_before = game['homePitcher']
                    elif game['awayTeam'] == team_id:
                        pitcher_before = game['awayPitcher']
                    if pitcher_before != pitcher_d99:
                        before_idx = rotation.index(pitcher_before)+len(teams_d100[team_id]['rotation'])
                        slot_99_idx = 1+game_idx+before_idx
                        break
                # Now determine the D100 pitcher.
                # The algorithm is *probably* the second available pitcher after the D99 pitching slot.
                slot_100_idx = slot_99_idx + 1 # Start here
                verified_100 = False
                skippedone = False
                while not verified_100:
                    pitcher_d100 = list(mike.get_player(rotation[slot_100_idx]).values())[0]
                    pitcher_mods = pitcher_d100['permAttr']+pitcher_d100['seasAttr']+pitcher_d100['itemAttr']
                    if not any(mod in pitcher_mods for mod in inactive_mods) and pitcher_d100['id']:
                        if not skippedone: # Skip the first available pitcher
                            slot_100_idx += 1
                            skippedone=True
                            continue
                        else: # This is it!!
                            verified_100 = True
                    else:
                        slot_100_idx += 1
                        continue
                # Now that we've confirmed the pitcher for this game, add to the stand-in games object
                if team_side == 'homeTeam':
                    games[idx]['homeTeam'] = team_id
                    games[idx]['homeOdds'] = 0.500 # Unknown odds!
                    games[idx]['homePitcher'] = pitcher_d100['id']
                    games[idx]['homePitcherName'] = pitcher_d100['name']
                elif team_side == 'awayTeam':
                    games[idx]['awayTeam'] = team_id
                    games[idx]['awayOdds'] = 0.500 # Unknown odds!
                    games[idx]['awayPitcher'] = pitcher_d100['id']
                    games[idx]['awayPitcherName'] = pitcher_d100['name']
    # Otherwise, just get tomorrow's games normally
    else:
        games = mike.get_games(season, tomorrow)

    # Get stadiums for determining if pitchers are faxable
    stadiums = {}
    stadiums_query = requests.get('https://api.sibr.dev/chronicler/v2/entities?type=stadium').json()['items']
    for stadium in stadiums_query:
        stadiums[stadium['data']['id']] = stadium['data']

    # Get pitchers
    pitchers = {}
    for game in games.values():
        stadium_id = mike.get_team(game['homeTeam'])['stadium']
        # Pitcher is faxable if it is a home game for them, their stadium has fax machines, and the weather isn't Sun 2 or Black Hole
        fax_machine = True if 'FAX_MACHINE' in stadiums[stadium_id]['mods'] and game['weather'] not in [1,14] else False
        pitchers[game['homePitcher']] = {
            'team': teams_shorten[game['homeTeam']],
            'name': game['homePitcherName'],
            'odds': round(game['homeOdds'],3),
            'faxable': fax_machine,
            'multiplier': 0
        }
        pitchers[game['awayPitcher']] = {
            'team': teams_shorten[game['awayTeam']],
            'name': game['awayPitcherName'],
            'odds': round(game['awayOdds'],3),
            'faxable': False,
            'multiplier': 0
        }

    # Get pitcher payout multiplier
    pitcher_details = mike.get_player(list(pitchers.keys()))
    for pitcher_id in pitcher_details:
        # Determine payout multiplier
        player_mods = pitcher_details[pitcher_id]['permAttr']+pitcher_details[pitcher_id]['seasAttr']+pitcher_details[pitcher_id]['itemAttr']
        multiplier = 1
        if 'DOUBLE_PAYOUTS' in player_mods:
            multiplier += 1
        if 'CREDIT_TO_THE_TEAM' in player_mods:
            multiplier += 4
        # Check if this player has a mod preventing them from making money
        inactive_mods = ['ELSEWHERE','SHELLED','LEGENDARY','REPLICA','NON_IDOLIZED']
        can_earn = int(not any(mod in player_mods for mod in inactive_mods))
        if not can_earn:
            multiplier = 0
        pitchers[pitcher_id]['multiplier'] = multiplier

    # Sort by multiplier
    pitchers_lists = [list(pitcher.values()) for pitcher in pitchers.values()]
    pitchers_lists.sort(key = lambda x: x[4], reverse=True)

    # Pad to 24 pitchers
    while len(pitchers_lists) < 24:
        pitchers_lists.append(['','','','',''])

    # Get individual columns
    # teams = [[pitcher[0]] for pitcher in pitchers_lists]
    pitcher_names = [pitcher[0:2] for pitcher in pitchers_lists]
    pitcher_other = [pitcher[2:] for pitcher in pitchers_lists]
    # multipliers = [[pitcher[2]] for pitcher in pitchers_lists]
    # odds = [[pitcher[3]] for pitcher in pitchers_lists]
    # faxable = [[pitcher[4]] for pitcher in pitchers_lists]

    # Add tomorrow's pitchers to spreadsheet
    worksheet.update('A4:B', pitcher_names)
    worksheet.update('I4:K', pitcher_other)
    # worksheet.update('I4', odds)
    # worksheet.update('J4', faxable)
    # worksheet.update('K4', multipliers)
    worksheet.update('F1', [[tomorrow]])

    logging.info("Updated tomorrow's pitchers.")

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
