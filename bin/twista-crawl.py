import json
import argparse

import twibot.streaming as twibot

parser = argparse.ArgumentParser()
parser.add_argument('--crawl', type=argparse.FileType('r'), help="Web pages to crawl for Twitter accounts (json format)", required=True)
parser.add_argument('--out', type=argparse.FileType('w'), help="File to store crawled Twitter accounts (json format)", required=True)

args = parser.parse_args()

crawl = json.loads(args.crawl.read())

follow = {}
for category, links in crawl.items():
    follow[category] = []
    for link in links:
        follow[category].extend(twibot.crawl(link['url'], link['follow_depth']))

json.dump(follow, args.out, indent=3)
