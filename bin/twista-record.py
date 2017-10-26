#!/usr/bin/env python
import time
import json
from datetime import datetime

import twista.streaming as twibot
import atexit

import argparse

parser = argparse.ArgumentParser()
parser.add_argument('--follow', type=argparse.FileType('r'), help="Twitter accounts to follow (json file)", required=True)
parser.add_argument('--language', type=str, help='Only record tweets of a specific language. ISO code (en for English, de for German, ...)', required=False, default='de')
parser.add_argument('--key', type=str, help="Twitter API account key", required=True)
parser.add_argument('--secret', type=str, help="Twitter API account secret", required=True)
parser.add_argument('--token', type=str, help="Twitter API token", required=True)
parser.add_argument('--token_secret', type=str, help="Twitter API token secret", required=True)

# We need some parameters here:
# Adjust every n minutes
# TOP n retweeter haunting
# TOP m hashtags tracking

args = parser.parse_args()

screen_names = []
if args.follow:
    data = json.loads(args.follow.read())
    for names in data.values():
        screen_names.extend(names)

ids = twibot.get_user_ids(
    key=args.key, secret=args.secret, token=args.token, token_secret=args.token_secret,
    screen_names=screen_names
)

tracking = None

def top(n, values):
    return list(values.frequencies(top=n).keys())

@atexit.register
def closestream():
    print("Closing stream")
    if tracking:
        print("Closing following stream")
        tracking.disconnect()


while True:
    try:
        # Start the tracking
        if not tracking:
            tracking = twibot.stream(key=args.key, secret=args.secret, token=args.token, token_secret=args.token_secret, language=args.language, follow=ids)

        if datetime.now().hour == 2:
            print("Disconnecting")
            tracking.disconnect()
            time.sleep(30)
            following = None

    except Exception as ex:
        print("Stream malfunction due to " + str(ex))
        print("Restarting the stream in 30 seconds")
        tracking = None
        time.sleep(30)
