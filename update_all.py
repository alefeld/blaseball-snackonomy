import statsheets
import hitterstats
import pitcherstats
import tomorrowpitchers
import weathersnacks
import betting
import datetime
import logging

spreadsheet_ids = { # Live Seasons
    19: '1_p6jsPxMvO0nGE-fiqGfilu-dxeUc994k2zwAGNVNr0',
    20: '1EAqMvv2KrC9DjlJdlXrH_JXmHtAStxRJ661lWbuwYQs',
    21: '1DBCpsYlDOft5wve7IKTXAH-3zeoZIUy7A_R4a5uiYz8',
    22: '1nC8ZU0dz2kyOH4w78jIcitMdhk9KhVKbKBSXC1QEkXY',
    23: '1jAHAHGgjpZp_PGDyedEvSSJVY-7Sq9bVkMcMTZjSBtg',
    24: '12cbSlctxlukuUIxb9T9eo2lIcMmnEqvI7dkF9906a_Q',
    25: '1UPDfwQh-kXsUUQUArYDGa1ViZ9Pdmt-m4D7Ji46w6-8'
}

# spreadsheet_ids = { # Retrospective
#    24: '1_BZqjYwEMoZTSahwS-zGvsFi0JKt3nS5Vsrp1oPRkLE',
#    23: '12uSogDqFuB-GS-3EzKe4KVa6NUZJ7LFDpWIOibaab5k',
#    22: '1xtvNRnKcPbCQXqISacCuXZnA9uQWv09WFNjIKlHY-Ao',
#    21: '1Pdolq8b1xWzScagWHYSNzwijFeL0xT3pusQvRygPHyg',
#    20: '1DqYQS0nOS0nZCmsE_gEY6jeCoUfWW_2Zec1PEqHM_A0',
#    19: '1RkM938JPvm5J4dRUNUyPlam9VfJE28KO0Ml5x-_R6pM',
#    18: '1pwyzZYCV656jqsY-TCdAAzlqriHUFdjImm8bzg80SLY',
#    17: '1CRCIptYHsJmyXvR3dgwxugCtDT3SX2sMRHuD4KCRmcw',
#    16: '1QrhOdiodB9lLAGzc8ycMP0xLqHIkVc7wDqU9kGbnKAE',
#    15: '1ZaIIFDNcAw3cCdoIvUqmCSHp18gSL1rpupJu23UcAaM',
#    14: '1AicVy-Jd7VZm96Qjg2rfWUvoa99lXpXcJFi8RDJMAnw',
#    13: '1ygHLw8SHfWTepK14V2zPOWnzoKI9AuDpok48DgWdfIM',
#    12: '1hpBJw2f1IGoZ-Xmbox5NJTGn0EQTeamtdke8f4LUroo',
#    11: '1oQJrEjcnpBhUEfm3cQfr2N9vsAzzdQuh9U695vhft7o',
#    10: '1V9m9fdjfs5LZDMeABFW00BH8Ct5KRWoxZ9sdPjrC3E4',
#     9: '1BikEjHCCC1URt7FOGQPt1z-bTJAtMfhAvhX-BWqJMhk',
#     8: '1byw1Ry_BIrR8oppo80l2XSTH_21AJ1-41JuGzy0Nxy4',
#     7: '11mQM7FLEE6wQTA4T8LroBdXyHwrt9OCDxKEMgFYkkI8',
#     6: '1O7GCmfD6GfHWUFQgcb7vAbpHj6gsOrWNJHn5CLKr4pI',
#     5: '1lktwWmP35hRG56Gc5v08fBmyxP9bMmr11xDh1mys-go',
#     4: '13NC_HCu6EJmsbVSdz6X0XokZ_WZ07iNWEs1zyXQl3kc',
#     3: '10iatp4K_ipe00SkiqbEWmRY1IjCk87xmlJkAselPvgE',
#     2: '1GcVNevWvG7CYlu_KloOVb5Af26_knNi0im8qhPpxMlE',
#     1: '1wMWV-MWzyYhtJNuECZdFh2RFlMuRcsD5AN2XWHuEuuc'
# }

def update_all(spreadsheet_ids=spreadsheet_ids, season=None):
    tomorrowpitchers.update(spreadsheet_ids)
    weathersnacks.update(spreadsheet_ids, season)
    statsheets.update(season)
    hitterstats.update(spreadsheet_ids, season)
    pitcherstats.update(spreadsheet_ids, season)
    betting.update(spreadsheet_ids, season)

if __name__ == "__main__":
    logging.basicConfig(format = '%(message)s',
                        level = logging.INFO)
    logging.info("Start Timestamp: {:%Y-%b-%d %H:%M:%S}".format(datetime.datetime.now()))
    # update_all()
    for season in range(22,25):
        logging.info("Processing season {}...".format(season))
        update_all(season=season)
    logging.info("End Timestamp: {:%Y-%b-%d %H:%M:%S}".format(datetime.datetime.now()))
