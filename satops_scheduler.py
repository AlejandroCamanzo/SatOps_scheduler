import configparser
import requests
import ast
import os
import numpy as np
from dateutil import tz
# Beyond library for orbital propagation using SGP4
from beyond.io.tle import Tle
from beyond.frames import create_station
from beyond.dates import Date, timedelta
# Google API for integration with Google Calendar
from googleapiclient.discovery import build
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials


def main():
    # Read configuration file
    config = configparser.ConfigParser()
    config.read("config.ini")
    print(config.sections())
    # User configuration
    general_settings = config['Settings']
    min_elevation_deg = general_settings['min_elevation_deg']
    local_timezone = general_settings['local_timezone']
    start_delta_days = general_settings['start_delta_days']
    stop_delta_hours = general_settings['stop_delta_hours']
    calendar_settings = config['Calendar']
    calendar_id = calendar_settings['calendar-id']

    scopes = ['https://www.googleapis.com/auth/calendar.events']
    start = Date.now() + timedelta(days=float(start_delta_days))
    stop = timedelta(hours=float(stop_delta_hours))
    step = timedelta(seconds=60)

    # The file token.json stores the user's access and refresh tokens, and is
    # created automatically when the authorization flow completes for the first
    # time.
    creds = None
    if os.path.exists('token.json'):
        creds = Credentials.from_authorized_user_file('token.json', scopes)
    # If there are no (valid) credentials available, let the user log in.
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            print("Able to refresh")
            creds.refresh(Request())
        else:
            print("Unable to refresh")
            flow = InstalledAppFlow.from_client_secrets_file(
                'credentials.json', scopes)
            creds = flow.run_local_server(port=0)
        # Save the credentials for the next run
        with open('token.json', 'w') as token:
            token.write(creds.to_json())
    else:
        print("Found valid token")

    service = build('calendar', 'v3', credentials=creds)

    for sat in config.items('Satellites'):
        sat_name = sat[1]
        print("Scheduling passes for: {}".format(sat_name))

        # Get current TLE from Celestrak
        url = 'https://celestrak.com/NORAD/elements/active.txt'
        r = requests.get(url, allow_redirects=True)
        open('tle.txt', 'wb').write(r.content)
        lines = open('tle.txt', 'r').readlines()

        # Parse TLE file to search for Satellite TLE
        sat = False
        cnt = 0
        tle0 = None
        tle1 = None
        tle2 = None

        for line in lines:
            if sat_name in line:
                print('satellite found')
                sat = True
            if sat:
                if cnt == 0:
                    tle0 = line
                elif cnt == 1:
                    tle1 = line
                elif cnt == 2:
                    tle2 = line
                elif cnt > 2:
                    break
                cnt += 1
        # Safety check if satellite is not found
        if not sat:
            print("Satellite not found in TLEs!")
            exit(1)

        # Parse TLE
        tle = Tle(tle0 + tle1 + tle2).orbit()

        # Create a station from which to compute the pass
        for gs in config.items('Ground Stations'):
            gs = ast.literal_eval(gs[1])

            gs_loc = (float(gs.get('latitude_deg')), float(gs.get('longitude_deg')), float(gs.get('altitude_m')))
            gs_name = gs.get('gs-name')

            gs = create_station(gs_name, gs_loc)

            max_elev = 0
            aos_time = None
            los_time = None
            max_time = None

            print("Scheduling passes of {} over {}".format(sat_name,gs_name))
            print("Location {}".format(gs_loc))

            for orb in gs.visibility(tle, start=start, stop=stop, step=step, events=True):
                if orb.event and orb.event.info.startswith("AOS"):
                    aos_time = orb.date
                if orb.event and orb.event.info.startswith("MAX"):
                    max_elev = np.degrees(orb.phi)
                    max_time = orb.date
                if orb.event and orb.event.info.startswith("LOS"):
                    los_time = orb.date

                    if max_elev > float(min_elevation_deg):
                        local_aos = aos_time.datetime + aos_time.datetime.replace(
                            tzinfo=tz.gettz(local_timezone)).utcoffset()

                        event = {
                            'summary': '{} AoS: {}:{}, {:.2f}º'.format(sat_name,
                                                                       str(local_aos.isoformat()).split("T")[1].split(":")[
                                                                           0],
                                                                       str(local_aos.isoformat()).split("T")[1].split(":")[
                                                                           1], max_elev),
                            'location': 'LEO',
                            'description': 'Automated event created for {} operational pass over GS {}'.format(sat_name,
                                                                                                               gs_name),
                            'start': {
                                'dateTime': str(aos_time - timedelta(minutes=10)).split()[0],
                                'timeZone': 'UTC',
                            },
                            'end': {
                                'dateTime': str(los_time + timedelta(minutes=10)).split()[0],
                                'timeZone': 'UTC',
                            },
                        }
                        event = service.events().insert(calendarId=calendar_id, body=event).execute()
                        print('Event created: %s' % (event.get('htmlLink')))
                        print("     AOS : {}".format(aos_time))


if __name__ == '__main__':
    main()