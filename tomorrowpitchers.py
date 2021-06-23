import blaseball_mike.database as mike
import gspread
import logging
import requests

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

    # Earlsiesta and latesiesta mess up the "tomorrow" thing
    if sim['phase'] in [3,5]:
        tomorrow = sim['day']+1
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
            'name': game['homePitcherName'],
            'odds': game['homeOdds'],
            'faxable': fax_machine,
            'multiplier': 0
        }
        pitchers[game['awayPitcher']] = {
            'name': game['awayPitcherName'],
            'odds': game['awayOdds'],
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
            multiplier = 2
        if 'CREDIT_TO_THE_TEAM' in player_mods:
            multiplier = 5
        # Check if this player has a mod preventing them from making money
        inactive_mods = ['ELSEWHERE','SHELLED','LEGENDARY','REPLICA','NON_IDOLIZED']
        can_earn = int(not any(mod in player_mods for mod in inactive_mods))
        if not can_earn:
            multiplier = 0
        pitchers[pitcher_id]['multiplier'] = multiplier

    # Sort by multiplier
    pitchers_lists = [list(pitcher.values()) for pitcher in pitchers.values()]
    pitchers_lists.sort(key = lambda x: x[3], reverse=True)

    # Pad to 24 pitchers
    while len(pitchers_lists) < 24:
        pitchers_lists.append(['','','',''])

    # Get individual columns
    pitcher_names = [[pitcher[0]] for pitcher in pitchers_lists]
    pitcher_other = [pitcher[1:] for pitcher in pitchers_lists]
    # multipliers = [[pitcher[1]] for pitcher in pitchers_lists]
    # odds = [[pitcher[2]] for pitcher in pitchers_lists]
    # faxable = [[pitcher[3]] for pitcher in pitchers_lists]

    # Add tomorrow's pitchers to spreadsheet
    worksheet.update('B4', pitcher_names)
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
        21: '1DBCpsYlDOft5wve7IKTXAH-3zeoZIUy7A_R4a5uiYz8'
    }
    update(spreadsheet_ids)
