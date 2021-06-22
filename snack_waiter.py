from sseclient import SSEClient
import datetime
import json
import logging
import update_all

logger = logging.FileHandler('waiter.log', 'w')
logging.basicConfig(format = '%(message)s',
                    level = logging.INFO,
                    handlers = [logger])

stream = SSEClient('http://blaseball.com/events/streamData', retry=1000)

phase_last = -1
season_last = -1
day_last = -1
siesta_processed = False
for message in stream:
    # At seemingly fixed intervals, the stream sends an empty message
    if not str(message):
        continue
    data = json.loads(str(message))
    # Sometimes the stream just sends fights
    if 'games' not in data['value']:
        continue
    # This should always work, though
    games = json.loads(str(message))['value']['games']
    day = games['sim']['day']
    season = games['sim']['season']
    phase = games['sim']['season']
    schedules = games['schedule']

    # If this day hasn't been processed, run if games are finished. Also run if we switch phases
    if day != day_last or season != season_last or phase != phase_last:
        all_finished = all([schedule['finalized'] for schedule in schedules])
        if all_finished or (day in [28,73] and not siesta_processed):
            logging.info("Waiter is now running snack errands.")
            logging.info("Start Timestamp: {:%Y-%b-%d %H:%M:%S}".format(datetime.datetime.now()))
            update_all.update_all()
            season_last = season
            day_last = day
            phase_last = phase
            if day in [28,73]:
                siesta_processed = True
            if day in [29,74]:
                siesta_processed = False
            logging.info("End Timestamp: {:%Y-%b-%d %H:%M:%S}".format(datetime.datetime.now()))
    else:
        pass
