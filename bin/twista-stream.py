#!/usr/bin/env python
import time
import json
from datetime import datetime

import twibot.streaming as twibot

import argparse

parser = argparse.ArgumentParser()
parser.add_argument('--follow', type=argparse.FileType('r'), help="Twitter accounts to follow (json file)", required=True)
parser.add_argument('--key', type=str, help="Twitter API account key", required=True)
parser.add_argument('--secret', type=str, help="Twitter API account secret", required=True)
parser.add_argument('--token', type=str, help="Twitter API token", required=True)
parser.add_argument('--token_secret', type=str, help="Twitter API token secret", required=True)

args = parser.parse_args()

data = json.loads(args.follow.read())
screen_names = sum([names for names in data.values()], [])

ids = twibot.get_user_ids(
    key=args.key, secret=args.secret, token=args.token, token_secret=args.token_secret,
    screen_names=screen_names
)

streaming = None
while True:
    try:
        # Start the streaming
        if not streaming:
            print("(Re-)Connecting")
            streaming = twibot.stream(key=args.key, secret=args.secret, token=args.token, token_secret=args.token_secret, follow=ids)

        # Check every hour to disconnect the stream in the night
        time.sleep(60 * 60)
        if datetime.now().hour == 2:
            print("Disconnecting")
            streaming.disconnect()
            time.sleep(30)
            streaming = None

    except Exception as ex:
        print("Stream malfunction due to " + str(ex))
        print("Restarting the stream in 30 seconds")
        streaming = None
        time.sleep(30)
