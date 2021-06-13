import blaseball_mike.database as mike
import gspread

def update(spreadsheet_ids):
    '''
    Updates weather values in this season's snack spreadsheet
    '''

    print("Updating weather stats...")

    # Get current season
    sim = mike.get_simulation_data()
    season = sim['season']+1
    spreadsheet_id = spreadsheet_ids[season]

    # Connect to spreadsheet
    credentials = gspread.service_account()
    worksheet = credentials.open_by_key(spreadsheet_id).worksheet('Weather Snacks')

    # Black Hole
    events_bh = mike.get_feed_global(season=season, limit=200, type_=30)
    # url = https://www.blaseball.com/database/feed/global?limit=200&season=18&type=30
    bh_activations = len(events_bh)
    bh_jampacked = len([event for event in events_bh if "worms collect" in event['description'].lower()])
    bh_payouts = bh_activations + bh_jampacked

    # Sun 2
    events_sun2 = mike.get_feed_global(season=season, limit=200, type_=31)
    # url = https://www.blaseball.com/database/feed/global?limit=200&season=18&type=31
    sun2_activations = len(events_sun2)
    sun2_glazed = len([event for event in events_sun2 if "tacos collect" in event['description'].lower()])
    sun2_payouts = sun2_activations + sun2_glazed

    # Solar Eclipse
    events_eclipse = mike.get_feed_global(season=season, limit=200, type_=54)
    # url = https://www.blaseball.com/database/feed/global?limit=200&season=18&type=54
    incinerations = len([event for event in events_eclipse if "rogue umpire incinerated" in event['description'].lower()])/2

    # Flooding
    events_flood = mike.get_feed_global(season=season, limit=500, type_=62)
    # url = https://www.blaseball.com/database/feed/global?limit=500&season=18&type=62
    flood_activations = len(events_flood)
    events_swept = mike.get_feed_global(season=season, limit=500, type_=106)
    # url = https://www.blaseball.com/database/feed/global?limit=500&season=18&type=106
    flood_payouts = len([event for event in events_swept if "swept elsewhere" in event['description'].lower()])

    # Consumers
    events_consumers = mike.get_feed_global(season=season, limit=500, type_=67)
    # url = https://www.blaseball.com/database/feed/global?limit=500&season=18&type=67
    attacks = len([event for event in events_consumers if "consumers" in event['description'].lower()])

    # Update sheet
    payload = [
        [bh_activations, bh_payouts], 
        [sun2_activations, sun2_payouts], 
        [incinerations, incinerations],
        [flood_activations, flood_payouts], 
        [attacks, attacks]
    ]
    worksheet.update('C2:D', payload)

    print("Weather stats updated.")

if __name__ == "__main__":
    spreadsheet_ids = {
        19: '1_p6jsPxMvO0nGE-fiqGfilu-dxeUc994k2zwAGNVNr0',
        20: '1EAqMvv2KrC9DjlJdlXrH_JXmHtAStxRJ661lWbuwYQs'
    }
    update(spreadsheet_ids)
