from sseclient import SSEClient
import datetime
import json
import update_all

stream = SSEClient('http://blaseball.com/events/streamData')

season_last = -1
day_last = -1
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
    schedules = games['schedule']

    # If this day hasn't been processed, run if games are finished
    if day != day_last or season != season_last:
        all_finished = all([schedule['finalized'] for schedule in schedules])
        if all_finished:
            print("Start Timestamp: {:%Y-%b-%d %H:%M:%S}".format(datetime.datetime.now()))
            update_all.update_all()
            season_last = season
            day_last = day
            print("End Timestamp: {:%Y-%b-%d %H:%M:%S}".format(datetime.datetime.now()))
    else:
        pass
