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

    with open('snackonomy_update.log','w') as logfile:
        logfile.write("Last run: {}".format(datetime.datetime.now()))

if __name__ == "__main__":
    update_all()