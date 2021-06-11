import blaseball_mike.database as bb
import gspread

def update(spreadsheet_id):

    print("Updating tomorrow's pitchers...")

    # Connect to spreadsheet
    credentials = gspread.service_account()
    worksheet = credentials.open_by_key(spreadsheet_id).worksheet('Tomorrow\'s Pitchers')

    # Get tomorrow's game
    # bb uses 1-indexed seasons and days as input
    # blaseball.com returns 0-indexed seasons and days
    sim = bb.get_simulation_data()
    season = sim['season']+1
    tomorrow = sim['day']+2
    games = bb.get_games(season, tomorrow)

    # Check if today's games are finished. Tomorrow's pitchers could be wrong, otherwise.
    today = sim['day']+1
    games_today = bb.get_games(18,95).values()
    complete = [game['gameComplete'] for game in games_today]
    if not all(complete):
        print("Games not complete. Tomorrow's pitchers might be wrong, so waiting...")
        quit()

    # Get pitchers
    pitcher_ids = []
    for game in games:
        pitcher_ids.append(games[game]['homePitcher'])
        pitcher_ids.append(games[game]['awayPitcher'])

    # Get current pitcher names
    pitcher_names = []
    multipliers = []
    pitchers = []
    for pitcher_id in pitcher_ids:
        pitcher = bb.get_player(pitcher_id)[pitcher_id]
        player_mods = pitcher['permAttr']+pitcher['seasAttr']+pitcher['itemAttr']
        # Determine payout multiplier
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
        pitcher_names.append([pitcher['name']])
        multipliers.append([multiplier])
        pitchers.append((pitcher['name'], multiplier))

    # Sort by multiplier
    pitchers.sort(key = lambda x: x[1], reverse=True)
    pitcher_names = [[pitcher[0]] for pitcher in pitchers]
    multipliers = [[pitcher[1]] for pitcher in pitchers]

    # Add empty entries to clear out old pitchers during the playoffs
    while len(pitcher_names) < 24:
        pitcher_names.append([''])
    while len(multipliers) < 24:
        multipliers.append([''])

    # Add tomorrow's pitchers to spreadsheet
    worksheet.update('B4', pitcher_names)
    worksheet.update('H4', multipliers)
    worksheet.update('F1', [[tomorrow]])

    print("Updated tomorrow's pitchers.")

if __name__ == "__main__":
    update('1_p6jsPxMvO0nGE-fiqGfilu-dxeUc994k2zwAGNVNr0')