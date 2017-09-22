#!/usr/bin/env python
import json
from datetime import datetime
from twista.analysis import TwistaGraph

import argparse
parser = argparse.ArgumentParser()
parser.add_argument('--input', type=str, help='Pattern for input chunks of tweets to process, defaults to "chunk-*.json"', default='chunk-*.json')
parser.add_argument('--out', type=argparse.FileType('wb'), help="output graph file", required=True)
parser.add_argument('--start-date', type=lambda d: datetime.strptime(d, '%Y-%m-%d'), default=datetime(year=1970, month=1, day=1))
parser.add_argument('--end-date', type=lambda d: datetime.strptime(d, '%Y-%m-%d'), default=datetime.now())

args = parser.parse_args()

print("Building graph ... This may take some time ...")

graph = TwistaGraph.build(pattern=args.input, start=args.start_date, end=args.end_date)

print("Storing graph. This may take some time ...")
graph.write(args.out)
print(graph.info())