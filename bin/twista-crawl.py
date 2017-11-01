import json
import argparse

import twista.streaming as crawler

parser = argparse.ArgumentParser()
parser.add_argument('--crawl', type=argparse.FileType('r'), help="Web pages to crawl for Twitter accounts (json format)", required=True)
parser.add_argument('--out', type=argparse.FileType('w'), help="File to store crawled Twitter accounts (json format)", required=True)

args = parser.parse_args()

crawl = json.loads(args.crawl.read())

follow = {}
for category, links in crawl.items():
    screennames = []
    for link in links:
        screennames.extend(crawler.crawl(link['url'], link['follow_depth']))
    follow[category] = list(set([sn.lower() for sn in screennames]))

json.dump(follow, args.out, indent=3)
