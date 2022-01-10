# SatOps_scheduler
Google Calendar scheduler for satellite passes over any ground station, for operations planning and scheduling

# Requirements
 Needs a project in google apis and a credentials.json in the same directory as the .py
 Need to edit the config file to add calendar ID where events will be written

Required libraries:
- beyond ( https://pypi.org/project/beyond/ )
- google-api-python-client
- google-auth-oauthlib
- requests
- python-dateutil
 
# Detailed instructions 
First ensure the 'config.ini' file is set up to track the satellites you want over you ground station/s, also add the google calendar ID where you want to write the events to. You need to generate a 'credentials.json' file in your google account to write the events to the calendar of your choice (in https://console.cloud.google.com/apis/credentials ), you may have to generate a new project there
