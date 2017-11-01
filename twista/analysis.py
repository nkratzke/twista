import glob
from functools import reduce
import datetime
import pytz
import statistics as stat
import random
import numpy as np
import networkx as nx
from tqdm import tqdm
from dateutil import parser

import json
import html


class Concept:

    def __init__(self, data):
        self.raw_data = data

    def __getattr__(self, attr):
        if attr not in self.raw_data:
            return None
        return self.raw_data[attr]

    def size(self):
        return len(json.dumps(self.raw_data))

    def created_at(self):
        try:
            d = parser.parse(self.raw_data['created_at'])
            return d
        except Exception as ex:
            print(ex)
            print(json.dumps(self.raw_data, indent=3))
            print("Error - aborting")
            exit(1)

    def __str__(self):
        return json.dumps(self.raw_data, indent=3)


class User(Concept):

    def id(self):
        return self.raw_data['id_str']

    def screen_name(self):
        return self.raw_data['screen_name']

    def verified(self):
        return self.raw_data['verified']

    def statuses_count(self):
        return self.raw_data['statuses_count']

    def friends_count(self):
        return self.raw_data['friends_count']

    def followers_count(self):
        return self.raw_data['followers_count']


class Tweet(Concept):

    def id(self):
        return self.raw_data['id_str']

    def user(self):
        if 'user' not in self.raw_data: return None
        return User(self.raw_data['user'])

    def is_reply(self):
        if 'in_reply_to_status_id' not in self.raw_data: return None
        return self.raw_data['in_reply_to_status_id'] != None

    def is_quote(self):
        return self.quoted_status() != None and not self.is_retweet()

    def is_retweet(self):
        return self.retweeted_status() != None

    def is_status(self):
        return not (self.is_quote() or self.is_retweet() or self.is_reply())

    def is_deleted(self):
        return 'delete' in self.raw_data

    def is_withheld(self):
        return 'status_withheld' in self.raw_data

    def in_reply_to_screen_name(self):
        return self.raw_data['in_reply_to_screen_name']

    def in_reply_to_user_id(self):
        return self.raw_data['in_reply_to_user_id_str']

    def in_reply_to_status_id(self):
        return self.raw_data['in_reply_to_status_id_str']

    def has_user_mentions(self):
        if not 'entities' in self.raw_data: return []
        return len(self.user_mentions()) > 0

    def language(self):
        if 'lang' not in self.raw_data: return None
        return self.raw_data['lang']

    def user_mentions(self):
        if 'entities' not in self.raw_data: return []
        return [user['screen_name'] for user in self.raw_data['entities']['user_mentions']]

    def has_hashtags(self):
        return len(self.hashtags()) > 0

    def hashtags(self):
        if 'entities' not in self.raw_data: return []
        return [tag['text'].lower() for tag in self.raw_data['entities']['hashtags']]

    def has_urls(self):
        return len(self.urls()) > 0

    def urls(self):
        if 'entities' not in self.raw_data:
            return []
        return [url['expanded_url'] for url in self.raw_data['entities']['urls'] if url['expanded_url']]

    def quoted_status(self):
        if 'quoted_status' in self.raw_data:
            return Tweet(self.raw_data['quoted_status'])
        else:
            return None

    def retweeted_status(self):
        if 'retweeted_status' in self.raw_data:
            return Tweet(self.raw_data['retweeted_status'])
        else:
            return None

    def inner_tweets(self):
        tweets = []
        retweeted = self.retweeted_status()
        quoted = self.quoted_status()
        if retweeted:
            tweets.append(retweeted)
            tweets.extend(retweeted.inner_tweets())
        if quoted:
            tweets.append(quoted)
            tweets.extend(quoted.inner_tweets())
        return tweets

    def text(self):
        if 'extended_tweet' in self.raw_data:
            if 'full_text' in self.raw_data['extended_tweet']:
                return html.unescape(self.raw_data['extended_tweet']['full_text'])
        return html.unescape(self.raw_data['text'])


class Edge(Concept):

    def __init__(self, data, graph):
        self.raw_data = data
        self.graph = graph

    def created(self):
        return parser.parse(self.raw_data['created'])

    def is_status(self):
        return self.type == 'status'

    def is_retweet(self):
        return self.type == 'retweet'

    def is_quote(self):
        return self.type == 'quote'

    def is_reply(self):
        return self.type == 'reply'

    # TODO: Is that still necessary?
    def initiated_reply(self):
        return self.type == 'initiatedreply'

    def propagated(self, fct=1.25):
        return self.src_node().category(fct=fct)

    def src_node(self):
        return Node(self.src, self.graph)

    def dest_node(self):
        return Node(self.dest, self.graph)


class Node(Concept):

    def __init__(self, n, graph):
        node = dict(graph.node[n])
        node['id'] = n
        self.raw_data = node
        self.graph = graph

    def __eq__(self, other):
        return self.id == other.id

    def __hash__(self):
        return hash(self.id)

    def __ne__(self, other):
        return not self.__eq__(other)

    def created(self):
        return parser.parse(self.raw_data['created'])

    def is_internal(self):
        return self.type == 'internal'

    def is_user(self):
        return self.type == 'user'

    def categoryp(self):
        return TwistaList(self.tag).frequencies(norm=True)

    def category(self, fct=1.25):
        if not self.tag:
            return 'unknown'

        if self.initialtag:
            return self.tag[0]

        # fct threshold check
        freqs = TwistaList(self.tag).frequencies()
        m = max(freqs.values())
        avg = stat.mean(freqs.values())
        n = len(freqs.keys())
        if m < fct * avg and n > 1:
            return 'inconsistent'
        try:
            return stat.mode(self.tag)
        except:
            return 'inconsistent'

    def out_nodes(self, via=lambda e: True):
        nodes = []
        for e in self.out_edges().filter(via):
            node = Node(e.dest, self.graph)
            if node.type == 'user':
                nodes.append(Node(e.dest, self.graph))
            else:
                print(node)
        return TwistaList(nodes)

    def out_edges(self):
        edges = []
        for src, dest, key, data in self.graph.out_edges(nbunch=[self.id], data=True, keys=True):
            if src == self.id:
                edge = dict(self.graph[src][dest][key])
                edge['src'] = src
                edge['dest'] = dest
                edges.append(Edge(edge, self.graph))
        return TwistaList(edges)

    def in_nodes(self, via=lambda e: True):
        nodes = []
        for e in self.in_edges().filter(via):
            if self.graph.node[e.src]['type'] != 'internal':
                nodes.append(Node(e.src, self.graph))
        return TwistaList(nodes)

    def in_edges(self):
        edges = []
        for src, dest, key, data in self.graph.in_edges(nbunch=[self.id], data=True, keys=True):
            if dest == self.id:
                edge = dict(self.graph[src][dest][key])
                edge['src'] = src
                edge['dest'] = dest
                edges.append(Edge(edge, self.graph))
        return TwistaList(edges)


class TwistaGraph:

    def __init__(self, g):
        self.graph = g

    def initial_tagging(self, tagging={}):
        tags = {}
        for tag, users in tagging.items():
            for user in users:
                tags[user.lower()] = tag

        # Initial tagging of nodes
        for n in self.graph.nodes():
            try:
                if self.graph.node[n]['type'] == 'user':
                    self.graph.node[n]['initialtag'] = False
                    sn = self.graph.node[n]['screenname']
                    if sn in tags:
                        print(f"Initial tagging {sn} with tag {tags[sn]}")
                        self.graph.node[n]['tag'].append(tags[sn])
                        self.graph.node[n]['initialtag'] = True
                        self.graph.node[n]['category'] = tags[sn]
            except Exception as ex:
                print(ex)
                print(dict(self.graph.node[n]))

    '''
    Label propagation algorithm to propagate initial tags (categories) along edges. 
    This is used to categorize nodes according to retweeting behaviour from initially categorized nodes.
    :param max_rounds: 
    :param fct: final categorization threshold (defaults to 1.25, 
                that means a final category is only assigned to a node if the most propagated tag 
                is used 25% more often than other tags in average)
    :return reference on graph (to enable method chaining) 
    '''
    def propagate_tags(self, max_rounds=10, fct=1.25, tagging={}):
        self.initial_tagging(tagging=tagging)

        round = 0
        to_propagate = self.nodes().filter(lambda n: n.initialtag)

        processed = set()

        while round < max_rounds and to_propagate:
            round += 1
            print("Tag propagating round %i" % round)
            next_round = set()
            for src in tqdm(to_propagate, desc='Processing nodes'):
                processed.add(src)
                for dest in src.out_nodes(via=lambda e: e.is_retweet()):
                    before = dest.category(fct=fct)
                    category = src.category(fct=fct)
                    if category not in ['unknown', 'inconsistent']:
                        dest.tag.append(category)
                    now = dest.category(fct=fct)

                    if dest not in processed or now != before:
                        next_round.add(dest)
            to_propagate = next_round

        return self

    def write(self, file):
        g = nx.MultiDiGraph(self.graph)
        nx.write_gpickle(g, file)

    @staticmethod
    def load(file):
        g = nx.read_gpickle(file)
        return TwistaGraph(g)

    @staticmethod
    def add_to_graph(tweet, graph, last_observation_of):

        if type(tweet) is Tweet:
            usr = tweet.user()

            observed = tweet.created_at()

            if usr.id() not in last_observation_of or last_observation_of[usr.id()] < observed:
                last_observation_of[usr.id()] = observed
                graph.add_node(usr.id(),
                               screenname=usr.screen_name().lower(),
                               type='user',
                               tag=[],
                               friends=usr.friends_count(),
                               followers=usr.followers_count(),
                               statuses=usr.statuses_count(),
                               created=str(usr.created_at()),
                               observed=str(observed),
                               name=usr.name,
                               description=usr.description,
                               location=usr.location
                               )

            if tweet.is_status():
                graph.add_edge(usr.id(), 'public',
                    created=str(tweet.created_at()),
                    statusid=tweet.id(),
                    causingstatusid='',
                    type='status',
                    text=tweet.text(),
                    lang=tweet.language(),
                    propagated=[],
                    usermentions=tweet.user_mentions(),
                    hashtags=tweet.hashtags()
                )
                return

            if tweet.is_reply():
                src = tweet.user().id()
                dest = tweet.in_reply_to_user_id()
                sn = tweet.in_reply_to_screen_name().lower()
                if not graph.has_node(dest):
                    graph.add_node(dest,
                                   screenname=sn,
                                   type='user',
                                   tag=[],
                                   friends=0,
                                   followers=0,
                                   statuses=0,
                                   created=str(datetime.datetime(1970, 1, 1, 0, 0, 0, 0, tzinfo=pytz.utc)),
                                   observed=str(datetime.datetime(1970, 1, 1, 0, 0, 0, 0, tzinfo=pytz.utc)),
                                   location=''
                                   )

                graph.add_edge(src, dest,
                    created=str(tweet.created_at()),
                    statusid=tweet.id(),
                    causingstatusid=tweet.in_reply_to_status_id(),
                    type='reply',
                    text=tweet.text(),
                    lang=tweet.language(),
                    propagated=[],
                    usermentions=tweet.user_mentions(),
                    hashtags=tweet.hashtags()
                )

                return

            if tweet.is_retweet():
                src = tweet.retweeted_status().user()

                if src.id() not in last_observation_of or last_observation_of[src.id()] < observed:
                    last_observation_of[src.id()] = observed
                    graph.add_node(src.id(),
                                   screenname=src.screen_name().lower(),
                                   type='user',
                                   tag=[],
                                   friends=src.friends_count(),
                                   followers=src.followers_count(),
                                   statuses=src.statuses_count(),
                                   created=str(src.created_at()),
                                   observed=str(observed),
                                   location=src.location
                                   )

                dest = tweet.user().id()
                graph.add_edge(src.id(), dest,
                    created=str(tweet.created_at()),
                    statusid=tweet.id(),
                    causingstatusid=tweet.retweeted_status().id(),
                    type='retweet',
                    text=tweet.text(),
                    retweetedtext=tweet.retweeted_status().text(),
                    lang=tweet.language(),
                    propagated=[],
                    usermentions=tweet.user_mentions(),
                    hashtags=tweet.hashtags()
                )

                return

            if tweet.is_quote():
                src = tweet.quoted_status().user() #.id()
                if src.id() not in last_observation_of or last_observation_of[src.id()] < observed:
                    last_observation_of[src.id()] = observed
                    graph.add_node(src.id(),
                                   screenname=src.screen_name().lower(),
                                   type='user',
                                   tag=[],
                                   friends=src.friends_count(),
                                   followers=src.followers_count(),
                                   statuses=src.statuses_count(),
                                   created=str(src.created_at()),
                                   observed=str(observed),
                                   location=src.location
                                   )

                dest = tweet.user().id()
                graph.add_edge(src.id(), dest,
                               created=str(tweet.created_at()),
                               statusid=tweet.id(),
                               causingstatusid=tweet.quoted_status().id(),
                               type='quote',
                               text=tweet.text(),
                               quotedtext=tweet.quoted_status().text(),
                               lang=tweet.language(),
                               propagated=[],
                               usermentions=tweet.user_mentions(),
                               hashtags=tweet.hashtags()
                               )

                return

    @staticmethod
    def build(only=lambda tweet: True,
              pattern='chunk-*.json',
              start=datetime.datetime(year=1970, month=1, day=1),
              end=datetime.datetime.now()
              ):
        graph = nx.MultiDiGraph()
        graph.add_node('public', type='internal')

        last_observation_of = {}
        processed = set()
        start_date = start.replace(tzinfo=pytz.UTC)
        end_date = end.replace(tzinfo=pytz.UTC)

        files = glob.glob(pattern)
        for file in tqdm(files, desc="Loading"):
            try:
                content = open(file, encoding='utf-8', errors='replace').read()
                tweets_data = json.loads(content)

                for data in tweets_data:
                    try:
                        tweet = Tweet(data)
                        if tweet.is_deleted():
                            continue
                        if tweet.is_withheld():
                            continue
                        if tweet.created_at() < start_date:
                            continue
                        if tweet.created_at() > end_date:
                            continue
                        if tweet.id() in processed:
                            continue
                        if only(tweet):
                            processed.add(tweet.id())
                            TwistaGraph.add_to_graph(tweet, graph, last_observation_of)
                            # Process inner tweets from retweets and quotes
                            for inner in tweet.inner_tweets():
                                if inner.id() not in processed:
                                    processed.add(inner.id())
                                    TwistaGraph.add_to_graph(inner, graph, last_observation_of)

                    except Exception as e:
                        print("Error processing tweet %s, '%s': %s" % (tweet.id(), tweet.text(), str(e)))

            except Exception as e:
                print("Error processing file " + file + ": " + str(e))

        return TwistaGraph(graph)

    def info(self):
        return nx.info(self.graph)

    def hits_metric(self):
        g = nx.DiGraph(self.graph)
        hubs, authorities = nx.hits(g)
        nx.set_node_attributes(self.graph, 'hub', hubs)
        nx.set_node_attributes(self.graph, 'authority', authorities)
        return self

    def pagerank_metric(self):
        g = nx.DiGraph(self.graph)
        pr = nx.pagerank(g)
        nx.set_node_attributes(self.graph, 'pagerank', pr)
        return self

    def current_flow_metric(self):
        g = nx.Graph(self.graph)
        cf = nx.current_flow_betweenness_centrality(g)
        nx.set_node_attributes(self.graph, 'currentflow', cf)
        return self

    def betweenness_centrality(self):
        bn = nx.betweenness_centrality(self.graph)
        nx.set_node_attributes(self.graph, 'betweenness', bn)
        return self

    def in_degree_centrality(self):
        idc = nx.in_degree_centrality(self.graph)
        nx.set_node_attributes(self.graph, 'indegree', idc)
        return self

    def out_degree_centrality(self):
        odc = nx.out_degree_centrality(self.graph)
        nx.set_node_attributes(self.graph, 'outdegree', odc)
        return self


    '''
    Retrieves a text corpus from the graph.
    :param of: Filter function to select edges from the graph (default: all edges are considered)
    :param src: Filter function to select edges by source node (default: all nodes are considered)
    :param dest: Filter function to select edges by destination node (default: all nodes are considered)
    :param get: Mapping function to get values from selected edges (defaults to text attribute).
    :return List of texts (Strings) from selected edges - the corpus  
    '''
    def corpus(self, of=lambda e: True, src=lambda n: True, dest=lambda n: True, get=lambda e: e.text):
        edges = self.edges().filter(lambda e: of(e) and src(e.src_node()) and dest(e.dest_node()))
        return edges.map(lambda e: get(e))

    '''
    Generates an interaction matrix between marked groups of nodes. 
    This interaction matrix counts how many interactions between two groups have been observed.
    :param marking: A lambda function to identify groups, defaults to lambda n: n.category (so the standard tag propagation is considered)
    :param outgoing: A lambda function to filter outgoing nodes which should be considered, defaults to lambda n: True (so all outgoing nodes are considered)    
    :param incoming: A lambda function to filter incoming nodes which should be considered, defaults to lambda n: True (so all incoming nodes are considered)
    :return: A dictionary of markers to a dictionary of markers to integers.
                The following example makes this hopefully more obvious. 
                The markers 'unknown' and 'Linke' are outputs of the marking lambda.
                {
                   "unknown": {
                      "unknown": 12094,
                      ...
                      "Linke": 5315
                   },
                   ...
                   ,
                   "Linke": {
                      "unknown": 1266,
                      ...
                      "Linke": 14699
                   }
                }
    '''
    def interaction_matrix(self, marking=lambda n: n.category, outgoing=lambda o: True, incoming=lambda i: True):
        markers = self.nodes().map(marking).unique()

        matrix = {}
        for src in markers:
            matrix[src] = {}
            for dest in markers:
                matrix[src][dest] = 0

        grouped = self.nodes().group(by=marking)
        for src, nodes in grouped.items():
            for node in nodes:
                outgoing_nodes = node.out_nodes().filter(outgoing).frequencies(on=marking)
                for dest, n in outgoing_nodes.items():
                    matrix[src][dest] += n

                incoming_nodes = node.out_nodes().filter(incoming).frequencies(on=marking)
                for dest, n in incoming_nodes.items():
                    matrix[dest][src] += n

        return matrix

    def nodes(self):
        nodes = []
        for n in self.graph.nodes: #_iter():
            if self.graph.node[n]['type'] == 'user':
                nodes.append(Node(n, self.graph))
        return TwistaList(nodes)

    def edges(self):
        edges = []
        for src, dest, key, data in self.graph.edges(data=True, keys=True):
            edge = dict(self.graph[src][dest][key])
            edge['src'] = src
            edge['dest'] = dest
            edges.append(Edge(edge, self.graph))
        return TwistaList(edges)

    def delete_node(self, label):
        self.graph.remove_node(label)
        return self


class TwistaList:

    def __init__(self, items):
        self.entries = items

    def __add__(self, items):
        return TwistaList(self.items() + items.items())

    def __sub__(self, items):
        return TwistaList([entry for entry in self.entries if entry not in items.items()])

    def __getitem__(self, item):
        return self.entries[item]

    def __str__(self):
        return str(list(map(str, self.entries)))

    def __len__(self):
        return len(self.entries)

    def items(self):
        return self.entries

    def unique(self):
        return TwistaList(list(set(self.entries)))

    def count(self):
        return len(self)

    def flatten(self):
        flattened = []
        for entry in self.entries:
            flattened.extend(entry)
        return TwistaList(flattened)

    def sample(self, n=1, p=None):
        if p:
            n = round(p * len(self.entries))
        return TwistaList(random.sample(self.entries, k=n))

    def first(self):
        return self.entries[0]

    '''
    Adds an element to the end of the list.
    :param entry: Element to be added
    '''
    def append(self, entry):
        self.entries.append(entry)

    '''
    Removes an element from the list.
    :param entry: Entry to delete
    '''
    def remove(self, entry):
        self.entries.remove(entry)

    '''
    Generates a dictionary mapping items to their occurrences in the list.
    This is useful to count occurrences of items. 
    :param on: Optional lambda function than can be applied on each item of the list. Defaults to identity function.
    :param norm: Normalize occurences between [0 .. 1.0[
    :param percentile: Threshold percentile to consider (defaults to None; so, by default all data is considered)
    :param top: Threshold to consider the top n entries (defaults to None; so, by default all data is considered)
    :return: Decending sorted by value mapping (Dict) of items to occurrences considering percentile or top-n thresholds
    '''
    def frequencies(self, on=lambda i: i, percentile=None, top=None, norm=False):
        # Count
        ret = {}
        for entry in self.entries:
            needle = on(entry)
            if needle in ret:
                ret[needle] += 1
            else:
                ret[needle] = 1

        # Normalize
        if norm:
            total = sum(list(ret.values()))
            for entry in ret.keys():
                ret[entry] /= total

        # Sort
        ret = dict(sorted([(k, v) for k, v in ret.items()], key=lambda e: e[1], reverse=True))

        # Handle thresholds
        if percentile == None and top == None:
            return ret

        # Determine threshold for percentile n%
        if percentile:
            threshold = np.percentile(list(ret.values()), percentile)

        # Determine threshold for top-n
        if top:
            values = sorted(list(ret.values()), reverse=True)
            if not values:
                return ret
            threshold = values[:top][-1]

        # Get all above threshold
        filtered = {}
        for entry in ret:
            if ret[entry] >= threshold:
                filtered[entry] = ret[entry]

        return filtered

    def group(self, by=lambda i: i, on=lambda i: i):
        grouped = {}
        for entry in self.entries:
            attr = by(entry)
            if attr in grouped:
                grouped[attr].append(on(entry))
            else:
                grouped[attr] = TwistaList([on(entry)])
        return grouped

    def filter(self, predicate):
        return TwistaList(list(filter(predicate, self.entries)))

    '''
    Removes all None entries from the list.
    :return List without None entries
    '''
    def compact(self):
        return TwistaList([e for e in self.entries if e is not None])

    def map(self, function):
        return TwistaList(list(map(function, self.entries)))

    def reduce(self, operator):
        return reduce(operator, self.entries)

    def as_list(self):
        return self.entries