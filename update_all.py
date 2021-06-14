import statsheets
import hitterstats
import tomorrowpitchers
import weathersnacks
import datetime

spreadsheet_ids = {
    19: '1_p6jsPxMvO0nGE-fiqGfilu-dxeUc994k2zwAGNVNr0',
    20: '1EAqMvv2KrC9DjlJdlXrH_JXmHtAStxRJ661lWbuwYQs'
}

def update_all(spreadsheet_ids):
    statsheets.update()
    hitterstats.update(spreadsheet_ids)
    weathersnacks.update(spreadsheet_ids)
    tomorrowpitchers.update(spreadsheet_ids)

if __name__ == "__main__":
    print("Start Timestamp: {:%Y-%b-%d %H:%M:%S}".format(datetime.datetime.now()))
    update_all(spreadsheet_ids)
    print("End Timestamp: {:%Y-%b-%d %H:%M:%S}".format(datetime.datetime.now()))
