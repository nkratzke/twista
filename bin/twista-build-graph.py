#!/usr/bin/env python
import json
from datetime import datetime
from twista.analysis import TwistaGraph

import argparse
parser = argparse.ArgumentParser()
parser.add_argument('--input', type=str, help='Pattern for input chunks of tweets to process, defaults to "chunk-*.json"', default='chunk-*.json')
parser.add_argument('--out', type=argparse.FileType('wb'), help="output graph file", required=True)
parser.add_argument('--hits', action="store_true", help="Calculate HITS metric (hub, authority)")
parser.add_argument('--pagerank', action="store_true", help="Calculate pagerank metric")
parser.add_argument('--degree-centrality', action="store_true", help="Calculate degree centrality metric (in/out degree)")
parser.add_argument('--betweenness-centrality', action="store_true", help="Calculate betweenness centrality metric")
parser.add_argument('--start-date', type=lambda d: datetime.strptime(d, '%Y-%m-%d'), default=datetime(year=1970, month=1, day=1))
parser.add_argument('--end-date', type=lambda d: datetime.strptime(d, '%Y-%m-%d'), default=datetime.now())
parser.add_argument('--propagate-tags', type=argparse.FileType('r'), help="")

args = parser.parse_args()

print("Building graph ... This may take some time ...")

graph = TwistaGraph.build(pattern=args.input, start=args.start_date, end=args.end_date)

if args.hits:
    print("Calculating HITS metric ...")
    graph.hits_metric()

if args.pagerank:
    print("Calculating pagerank metric ...")
    graph.pagerank_metric()

if args.degree_centrality:
    print("Calculating in degree centrality ...")
    graph.in_degree_centrality()
    print("Calculating out degree centrality ...")
    graph.out_degree_centrality()

if args.betweenness_centrality:
    print("Calculating in betweenness centrality ...")
    graph.betweenness_centrality()

if args.propagate_tags:
    print("Tagging nodes")
    graph.propagate_tags(tagging=json.loads(args.propagate_tags.read()))

print("Storing graph. This may take some time ...")
graph.write(args.out)
print(graph.info())