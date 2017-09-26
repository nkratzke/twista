import json
import argparse

import twista.streaming as twibot

parser = argparse.ArgumentParser()
parser.add_argument('--crawl', type=argparse.FileType('r'), help="Web pages to crawl for Twitter accounts (json format)", required=True)
parser.add_argument('--out', type=argparse.FileType('w'), help="File to store crawled Twitter accounts (json format)", required=True)

args = parser.parse_args()

crawl = json.loads(args.crawl.read())

follow = {}
for category, links in crawl.items():
    follow[category] = []
    for link in links:
        if 'js_enabled' in link:
            js = link['js_enabled']
        else:
            js = False
        follow[category].extend(twibot.crawl(link['url'], link['follow_depth'], js_enabled=js))

json.dump(follow, args.out, indent=3)
