from flask import Flask, escape, request, Response, render_template
from py2neo import Graph
from collections import Counter
import json
import os

templates = os.path.join(os.path.dirname(os.path.realpath(__file__)), 'templates')
statics = os.path.join(os.path.dirname(os.path.realpath(__file__)), 'static')
app = Flask("Twista navigator", template_folder=templates, static_folder=statics)
graph = None

@app.route('/')
def hello():
    return render_template('base.html', title="Twista Navigator", content="Hello World")

@app.route('/tweet/<id>')
def tweet(id):
    result = graph.run("MATCH (t:Tweet{id: {id}}) RETURN collect(t)", id=id).evaluate()
    return as_json(result)

@app.route('/tweet/<id>/tags')
def tweet_related_tags(id):
    result = graph.run("MATCH (t:Tweet{id: {id}}) -[:REFERS_TO*]- (r:Tweet) -[:HAS_TAG]-> (tag:Tag) RETURN collect(tag.id)", id=id).evaluate()
    return as_json(Counter(result))

@app.route('/tweet/<id>/tweets')
def tweet_related_tweets(id):
    result = graph.run("MATCH (t:Tweet{id: {id}}) -[:REFERS_TO*]- (r:Tweet) RETURN r ORDER BY r.created_at DESCENDING", id=id)
    results = [r['r'] for r in result]
    return as_json(results)

@app.route('/tweet/<id>/users')
def tweet_related_users(id):
    result = graph.run("MATCH (t:Tweet{id: {id}}) -[:REFERS_TO*]- (r:Tweet) <-[:POST]-> (u:User) RETURN collect(u.screen_name)", id=id).evaluate()
    return as_json(Counter(result))

@app.route('/user/<id>')
def user(id):
    result = graph.run("MATCH (u:User{id: {id}}) RETURN u", id=id).evaluate()
    return as_json(Counter(result))


@app.route('/tweets/')
def tweets():
    result = graph.run("MATCH (t:Tweet) -[:REFERS_TO*]- (o:Tweet) WHERE t.type <> 'retweet' RETURN t, count(o) AS n ORDER BY n DESCENDING LIMIT 100").data()
    return render_template('base.html', tweets=[r['t'] for r in result])

@app.route('/search')
def search():
    searchstring = request.args.get("search")
    result = graph.run("""
        CALL db.index.fulltext.queryNodes('tweets', {search}) YIELD node, score
        WHERE node.type <> 'retweet'
        MATCH (user:User) -[:POSTS]-> (node:Tweet)
        OPTIONAL MATCH (node:Tweet) -[:REFERS_TO]-> (refers:Tweet)
        RETURN user, node, refers, score ORDER BY node.retweets DESCENDING, score DESCENDING, node.created_at DESCENDING
    """, search=searchstring)
    return render_template('base.html', tweets=[{ 'user': r['user'], 'tweet': r['node'], 'refers_to': r['refers'] } for r in result])


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