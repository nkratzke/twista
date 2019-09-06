from flask import Flask, escape, request, Response, render_template, redirect, url_for
from py2neo import Graph
from collections import Counter
from datetime import datetime, timedelta
import json
import os

templates = os.path.join(os.path.dirname(os.path.realpath(__file__)), 'templates')
statics = os.path.join(os.path.dirname(os.path.realpath(__file__)), 'static')
app = Flask("Twista navigator", template_folder=templates, static_folder=statics)
graph = None

@app.template_filter()
def render_tweet(tweet, of={}, ctx=[]):
    return render_template('tweet_snippet.html', tweet=tweet, user=of, ctx=ctx)

@app.route('/')
def hello():
    return redirect(url_for('search'))

@app.route('/tag/<id>')
def tweets_for_tag(id):
    tweets = [tweet['t'] for tweet in graph.run("""
        MATCH (tag:Tag{id: {id}}) <-[:HAS_TAG]- (t:Tweet)
        WHERE t.type <> 'retweet'
        RETURN t 
        ORDER BY t.created_at DESCENDING
        LIMIT 100
        """, id=id)]
    return render_template('tweets.html', tweets=tweets)

@app.route('/tweet/<id>')
def tweet(id):
    result = graph.run("MATCH (t:Tweet{id: {id}}) <-[:POSTS]- (u:User) RETURN t, u", id=id).data()
    tweet = result[0]['t']
    usr = result[0]['u']
    context = [{ 'tweet': ctx['tweet'], 'user': ctx['usr'] } for ctx in graph.run("""
        MATCH (:Tweet{id: {id}}) -[:REFERS_TO*]-> (tweet:Tweet) <-[:POSTS]- (usr:User)
        RETURN tweet, usr
        ORDER BY tweet.created_at DESCENDING
        """, id=id)]
    full_context = [{ 'tweet': ctx['ctx'], 'user': ctx['usr'] } for ctx in graph.run("""
        MATCH (:Tweet{id: {id}}) -[:REFERS_TO*]- (ctx:Tweet) <-[:POSTS]- (usr:User)
        RETURN ctx, usr
        ORDER BY ctx.created_at DESCENDING
        """, id=id)]

    usr_context = Counter([ctx['user'] for ctx in full_context]).most_common(100)

    return render_template('tweet.html', 
        tweet=tweet, 
        user=usr, 
        ctx=context, 
        full_ctx=full_context,
        user_ctx=usr_context
    )

@app.route('/user/<id>')
def user_as_html(id):
    result = graph.run("MATCH (u:User{id: {id}}) RETURN u", id=id).evaluate()
    tags = graph.run("""
        MATCH (u:User{id: {id}}) -[:POSTS]-> (t:Tweet) <-[:REFERS_TO*]- (refs:Tweet) -[:HAS_TAG]-> (tag:Tag)
        RETURN collect(tag.id)
        """, id=id).evaluate()

    retweeters = [r['rt'] for r in graph.run("""
        MATCH (u:User{id: {id}}) -[:POSTS]-> (:Tweet) <-[:REFERS_TO]- (:Tweet{type:'retweet'}) <-[:POSTS]- (rt:User)
        RETURN rt
        """, id=id).data()]

    return render_template('user.html', 
        user=result, 
        tags=Counter(tags).most_common(100),
        retweeters=Counter(retweeters).most_common(100)
    )

@app.route('/user/<id>/json')
def user_as_json(id):
    result = graph.run("MATCH (u:User{id: {id}}) RETURN u", id=id).evaluate()
    return as_json(Counter(result))

@app.route('/search')
def search():
    search_arg = request.args.get("search")

    if not search_arg:
        return render_template('base.html', tweets=[])

    since = (datetime.utcnow() - timedelta(days=7)).strftime("%Y-%m-%d")
    result = graph.run("""
        CALL db.index.fulltext.queryNodes('tweets', { search }) YIELD node AS tweet, score
        WHERE tweet.type <> 'retweet' AND tweet.retweets IS NOT NULL AND tweet.created_at > datetime({ since })
        RETURN tweet, score ORDER BY tweet.retweets DESCENDING, tweet.created_at DESCENDING, score DESCENDING
        LIMIT 100
    """, search=search_arg, since = since)
    return render_template('tweets.html', tweets=[t['tweet'] for t in result])


def as_json(data):
    return Response(json.dumps(data, indent=2, default=str), mimetype='application/json')

def start(settings):
    global graph
    url = settings['neo4j_url']
    usr = settings['neo4j_usr']
    pwd = settings['neo4j_pwd']

    graph = Graph(url, auth=(usr, pwd))

    print(statics)
    print(templates)

    app.run()