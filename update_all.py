import statsheets
import hitterstats
import pitcherstats
import tomorrowpitchers
import weathersnacks
import datetime
import logging

spreadsheet_ids = {
    19: '1_p6jsPxMvO0nGE-fiqGfilu-dxeUc994k2zwAGNVNr0',
    20: '1EAqMvv2KrC9DjlJdlXrH_JXmHtAStxRJ661lWbuwYQs',
    21: '1DBCpsYlDOft5wve7IKTXAH-3zeoZIUy7A_R4a5uiYz8',
    22: '1nC8ZU0dz2kyOH4w78jIcitMdhk9KhVKbKBSXC1QEkXY'
}

def update_all(spreadsheet_ids=spreadsheet_ids):
    tomorrowpitchers.update(spreadsheet_ids)
    weathersnacks.update(spreadsheet_ids)
    statsheets.update()
    hitterstats.update(spreadsheet_ids)
    pitcherstats.update(spreadsheet_ids)

if __name__ == "__main__":
    logging.basicConfig(format = '%(message)s',
                        level = logging.INFO)
    logging.info("Start Timestamp: {:%Y-%b-%d %H:%M:%S}".format(datetime.datetime.now()))
    update_all()
    logging.info("End Timestamp: {:%Y-%b-%d %H:%M:%S}".format(datetime.datetime.now()))
