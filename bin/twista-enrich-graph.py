#!/usr/bin/env python
import json
from twista.analysis import TwistaGraph

import argparse
parser = argparse.ArgumentParser()
parser.add_argument('--input', type=argparse.FileType('rb'), help="input graph file", required=True)
parser.add_argument('--out', type=argparse.FileType('wb'), help="output graph file", required=True)
parser.add_argument('--hits', action="store_true", help="Calculate HITS metric (hub, authority)")
parser.add_argument('--pagerank', action="store_true", help="Calculate pagerank metric")
parser.add_argument('--degree-centrality', action="store_true", help="Calculate degree centrality metric (in/out degree)")
parser.add_argument('--betweenness-centrality', action="store_true", help="Calculate betweenness centrality metric")
parser.add_argument('--lemmatize', action="store_true", help="Lemmatize all Tweets using part-of-speech tagging")
parser.add_argument('--propagate-tags', type=argparse.FileType('r'), help="Label nodes and propagte these labels")

args = parser.parse_args()

graph = TwistaGraph.load(args.input)

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

if args.lemmatize:
    print("Part of speech tagging (lemmatization and sentiment calculation)")
    graph.lemmatize()

print("Storing graph. This may take some time ...")
graph.write(args.out)
print(graph.info())