import blaseball_mike.database as bb
import statsheets
import hitterstats
import tomorrowpitchers
import weathersnacks
import datetime

spreadsheet_id = '1_p6jsPxMvO0nGE-fiqGfilu-dxeUc994k2zwAGNVNr0'

def update_all():
    statsheets.update()
    hitterstats.update(spreadsheet_id)
    weathersnacks.update(spreadsheet_id)
    tomorrowpitchers.update(spreadsheet_id)

if __name__ == "__main__":
    print("Start Timestamp: {:%Y-%b-%d %H:%M:%S}".format(datetime.datetime.now()))
    sim = bb.get_simulation_data()
    # if sim['phase'] in [0,13]:
    #     print("Siesta! Go to sleep!")
    else:
        update_all()
    print("End Timestamp: {:%Y-%b-%d %H:%M:%S}".format(datetime.datetime.now()))
