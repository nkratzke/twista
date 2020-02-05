from tqdm import tqdm
import gzip
import json
import copy
import os
import sys
import time
import subprocess
import click
import urllib
import tarfile
from pathlib import Path

import_tweets = """
    WITH {json} as data
    UNWIND data AS row
    MERGE (r:Tweet{id: row.id}) 
    SET r+=row, r.created_at=datetime(row.created_at), r.recorded_at=datetime(row.recorded_at)
    """

import_users = """
    WITH {json} as data
    UNWIND data AS row
    MERGE (r:User{id: row.id}) 
    SET r+=row, r.created_at=datetime(row.created_at), r.recorded_at=datetime(row.recorded_at)
    """

merge_posts = """
    WITH {json} as data
    UNWIND data AS row
    MATCH (t:Tweet{id: row.tweet_id})
    MATCH (u:User{id: row.user_id})
    MERGE (u) -[:POSTS]-> (t)
    """

merge_refers = """
    WITH {json} as data
    UNWIND data AS row
    MATCH (t:Tweet{id: row.tweet_id})
    MATCH (r:Tweet{id: row.ref_tweet_id})
    MERGE (t) -[:REFERS_TO]-> (r)
    """

merge_mentions = """
    WITH {json} AS data
    UNWIND data AS row
    MATCH (t:Tweet{id: row.tweet_id})
    MATCH (u:User{id: row.mentioned_id})
    MERGE (t) -[:MENTIONS]-> (u)
    """

create_tags = """
    WITH {json} AS data
    UNWIND data as tag
    MERGE (t:Tag{id:tag})
    """

merge_tags = """
    WITH {json} AS data
    UNWIND data as row
    MATCH (t:Tweet{id: row.tweet_id})
    MATCH (r:Tag{id: row.tag})
    MERGE (t) -[:HAS_TAG]-> (r)
    """

create_urls = """
    WITH {json} AS data
    UNWIND data as url
    MERGE (t:Url{id:url})
    """

merge_urls = """
    WITH {json} AS data
    UNWIND data as row
    MATCH (t:Tweet{id: row.tweet_id})
    MATCH (u:Url{id: row.url})
    MERGE (t) -[:HAS_URL]-> (u)
    """

def import_records(graph, records):

    # Generate indexes (if not exist)
    graph.run("CREATE CONSTRAINT ON (r:Tweet) ASSERT r.id IS UNIQUE")
    graph.run("CREATE INDEX ON :Tweet(created_at)")
    graph.run("CREATE INDEX ON :Tweet(type)")
    graph.run("CREATE CONSTRAINT ON (r:User) ASSERT r.id IS UNIQUE")
    graph.run("CREATE INDEX ON :User(created_at)")
    graph.run("CREATE INDEX ON :User(screen_name)")
    graph.run("CREATE CONSTRAINT ON (t:Tag) ASSERT t.id IS UNIQUE")
    graph.run("CREATE CONSTRAINT ON (u:Url) ASSERT u.id IS UNIQUE")
    graph.sync()

    q = "CALL db.indexes() YIELD indexName AS i, type AS t WHERE t = 'node_fulltext' RETURN collect(i)"
    existing = graph.run(q).single().value()
    if 'tweets' not in existing:
        graph.run("CALL db.index.fulltext.createNodeIndex('tweets', ['Tweet'], ['text'])")
        print("Created fulltext index for tweets")
    if 'users' not in existing:
        graph.run("CALL db.index.fulltext.createNodeIndex('users', ['User'], ['name', 'screen_name', 'description', 'location'])")
        print("Created fulltext index for users")
    graph.sync()

    # Import recordings (tweets and users)
    seen_tags = set()
    seen_urls = set()
    imported = [];
    if Path('imported.json').exists():
        with open('imported.json') as f:
            imported = json.load(f)
    
    tbd = sorted(list(set(records) - set(imported)))
    p = tqdm(tbd, desc="Importing", file=sys.stdout)
    for f in p:

        with gzip.open(f, "rb") as chunk:
            data = json.loads(chunk.read().decode("utf-8"))
            
            # Import users
            users = [d for d in data if d['type'] == 'user']
            p.set_description(f"Processing {p.n}/{p.total} (merging {len(users)} users)")
            graph.run(import_users, json=users)
            
            # Import tweets
            tweets = [d for d in data if d['type'] != 'user']
            imports = copy.deepcopy(tweets)
            for t in imports:
                t.pop('mentions', None)
                t.pop('mentioned_ids', None)
                t.pop('hashtags', None)
                t.pop('urls', None)
            p.set_description(f"Processing {p.n}/{p.total} (merging {len(tweets)} tweets)")
            graph.run(import_tweets, json=imports)
            graph.sync()
            
            # Generate post relations
            posts = [{ 'user_id': t['user'], 'tweet_id': t['id'] } for t in tweets if 'user' in t]
            p.set_description(f"Processing {p.n}/{p.total} (merging {len(posts)} posts)")
            graph.run(merge_posts, json=posts)

            # Generate refers_to relations
            refers = [{ 'tweet_id': t['id'], 'ref_tweet_id': t['refers_to'] } for t in tweets if 'refers_to' in t]
            p.set_description(f"Processing {p.n}/{p.total} (merging {len(refers)} referings)")
            graph.run(merge_refers, json=refers)

            # Generate mention relations
            mentions = [{ 'tweet_id': t['id'], 'mentioned_id': mid } for t in tweets for mid in t['mentioned_ids']]
            p.set_description(f"Processing {p.n}/{p.total} (merging {len(mentions)} mentions)")
            graph.run(merge_mentions, json=mentions)

            # Generate tag relations
            tags = set([tag for t in tweets for tag in t['hashtags']]) - seen_tags
            seen_tags = seen_tags.union(tags)
            tag_rels = [{'tweet_id': t['id'], 'tag': tag.upper()} for t in tweets for tag in t['hashtags']]
            p.set_description(f"Processing {p.n}/{p.total} (merge {len(tags)} new tags)")            
            graph.run(create_tags, json=list(tags))
            p.set_description(f"Processing {p.n}/{p.total} (merging {len(tag_rels)} taggings)")            
            graph.run(merge_tags, json=tag_rels)

            # Generate url relations
            urls = set([url for t in tweets for url in t['urls']]) - seen_urls
            seen_urls = seen_urls.union(urls)
            url_rels = [{'tweet_id': t['id'], 'url': url } for t in tweets for url in t['urls']]
            p.set_description(f"Processing {p.n}/{p.total} (merge {len(urls)} new urls)")            
            graph.run(create_urls, json=list(urls))
            p.set_description(f"Processing {p.n}/{p.total} (merging {len(url_rels)} url refers)")            
            graph.run(merge_urls, json=url_rels)
        
        imported.append(f)
        with open('imported.json', 'w') as f:
            json.dump(imported, f, indent=3)

def install_neo4j(config):
    if not Path('neo4j').exists():
        settings = json.load(open(config))
        url = "https://neo4j.com/artifact.php?name=neo4j-community-3.5.8-unix.tar.gz"
        click.echo(f"Downloading Neo4j [{ url }]")
        file, msg = urllib.request.urlretrieve(url, "neo4j.tar.gz")
        with tarfile.open(file) as tf:
            tf.extractall()
            os.system("mv neo4j*/ neo4j/")
            os.system(f"rm { file }")
            os.system(f"neo4j/bin/neo4j-admin set-initial-password '{ settings['neo4j_pwd'] }'")

def start_neo4j(config):
    if Path("neo4j").exists():
        while subprocess.getoutput("neo4j/bin/neo4j status") == "Neo4j is not running":
            click.echo("Starting Neo4j")
            os.system("neo4j/bin/neo4j start")
            time.sleep(5)

def stop_neo4j():
    if Path("neo4j").exists():
        click.echo("Stopping Neo4j")
        os.system("neo4j/bin/neo4j stop")