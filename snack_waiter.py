import datetime
import json
import logging
import requests
import time

import update_all

logger = logging.FileHandler('waiter.log', 'w')
logging.basicConfig(format = '%(message)s',
                    level = logging.INFO,
                    handlers = [logger])

phase_last = -1
season_last = -1
day_last = -1
siesta_processed = False
time_start = time.time()
while True:
    # try:
        # Poll sim, and schedule
    response = requests.get('https://api2.blaseball.com/sim')
    sim = json.loads(response.content)

    phase = sim['phase']
    season = sim['simData']['currentSeasonNumber']+1 ## ALSO NEED TO KNOW BETA/GAMMA/???
    day = sim['simData']['currentDay']+1

    # If this day hasn't been processed, run if games are finished.
    # Also run if phase changed and there are no games
    # Also if this is a day after siesta,
    if not sim['simData']['liveGames']:
        if day != day_last or season != season_last or phase != phase_last:
            schedules = ['schedule']
            logging.info("Waiter is now running snack errands.")
            logging.info("Start Timestamp: {:%Y-%b-%d %H:%M:%S}".format(datetime.datetime.now()))
            # # update_all.update_all()
            # season_last = season
            # phase_last = phase
            # # For siestas, don't register the day being done until games have finished
            # if day not in [28,73] or all_finished:
            #     day_last = day
            # if day in [28,73]:
            #     siesta_processed = True
            # elif day in [29,74]:
            #     siesta_processed = False
            # logging.info("End Timestamp: {:%Y-%b-%d %H:%M:%S}".format(datetime.datetime.now()))
    else:
        pass
    # except Exception as error:
    #     logging.error(error)
    #     # Wait five minutes if things break (site is down?)
    #     time.sleep(5)