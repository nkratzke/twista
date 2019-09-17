from flask import Flask, escape, request, Response, render_template, redirect, url_for, jsonify
from py2neo import Graph
from collections import Counter
from datetime import datetime as dt
from datetime import timedelta
import json
import os
from dateutil import parser
import random as rand
import string

templates = os.path.join(os.path.dirname(os.path.realpath(__file__)), 'templates')
statics = os.path.join(os.path.dirname(os.path.realpath(__file__)), 'static')
app = Flask("Twista navigator", template_folder=templates, static_folder=statics)
app.jinja_options['extensions'].append('jinja2.ext.do')
graph = None

@app.template_filter()
def render_tweet(tweet, of={}, ctx=[]):
    return render_template('tweet_snippet.html', tweet=tweet, user=of, ctx=ctx)

@app.template_filter()
def tweetlist(tweets):
    return render_template('tweet_list.html', tweets=tweets)

@app.template_filter()
def mark(content, link="", n=0):
    return f"<a href='{ link }'><span class='marker'>{ content }</span><span class='frequency'>{ n }</span></a>"

@app.template_filter()
def card(content, text="", title="", media="", actions=""):
    return render_template('card_snippet.html', title=title, text=content, media=media, actions=actions)

@app.template_filter()
def chip(content, data=None):
    if data:
        return "".join([
            f'<span class="mdl-chip mdl-chip--contact">',
            f'<span class="mdl-chip__contact mdl-color--teal mdl-color-text--white">{ data }</span>',
            f'<span class="mdl-chip__text">{ content }</span>',
            f'</span>'
        ])
    return f'<span class="mdl-chip"><span class="mdl-chip__text">{ content }</span></span>'

def link(content, url, classes=None):
    if classes:
        cs = " ".join(classes)
        return f"<a class={ cs } href='{ url }'>{ content }</a>"
    return f"<a href='{ url }'>{ content }</a>"

@app.template_filter()
def datetime(dt):
    return parser.parse(str(dt)).strftime("%Y-%m-%d %H:%M:%S")

@app.route('/')
def hello():
    return redirect(url_for('search'))

@app.route('/tags')
def trending_tags():
    print(request.args)
    begin = request.args.get("begin", default="1970-01-01")
    end = request.args.get("end", default=dt.now().strftime("%Y-%m-%d"))

    result = [(r['tag'], r['n']) for r in graph.run("""
        MATCH (tag:Tag) <-[:HAS_TAG]- (t:Tweet)
        WHERE t.created_at >= datetime({begin}) AND t.created_at <= datetime({end})
        RETURN tag.id AS tag, count(t) AS n
        ORDER BY n DESCENDING LIMIT 100
        """, begin=begin, end=end)]

    tags = [t for t, n in result[0:10]]
    timelines = graph.run("""
        UNWIND {tags} AS tg
        MATCH (t:Tweet) -[:HAS_TAG]-> (:Tag{id: tg})
        WHERE t.created_at >= datetime({begin}) AND t.created_at <= datetime({end})
        RETURN tg, date(t.created_at) as date, count(t) as n
        ORDER BY date
        """, tags=tags, begin=begin, end=end).data()
    data = { t: { 
            'xs': [str(e['date']) for e in timelines if e['tg'] == t],
            'ys': [e['n'] for e in timelines if e['tg'] == t]
        } for t in tags }

    return render_template('tags.html', tags=result, timelines=data)

@app.route('/tag/<id>')
def tweets_for_tag(id):

    begin = request.args.get("begin", default="1970-01-01")
    end = request.args.get("end", default=dt.now().strftime("%Y-%m-%d"))

    volume = [(r['date'], r['n']) for r in graph.run("""
        MATCH (:Tag{id: {id}}) <-[:HAS_TAG]- (t:Tweet)
        WHERE t.created_at >= datetime({ begin }) AND t.created_at <= datetime({ end })
        RETURN date(t.created_at) AS date, count(t) as n ORDER BY date
        """,id=id, begin=begin, end=end)]

    tweets = [{ 'tweet': tweet['t'], 'user': tweet['u'] } for tweet in graph.run("""
        MATCH (tag:Tag{id: {id}}) <-[:HAS_TAG]- (t:Tweet) <-[:POSTS]- (u:User)
        WHERE t.type <> 'retweet' AND t.created_at >= datetime({ begin }) AND t.created_at <= datetime({ end })
        RETURN t, u
        ORDER BY t.created_at DESCENDING
        LIMIT 100
        """, id=id, begin=begin, end=end)]

    tags = Counter(graph.run("""
        MATCH (tag:Tag{id: {id}}) <-[:HAS_TAG]- (t:Tweet) -[:HAS_TAG]-> (other:Tag)
        WHERE tag <> other AND t.created_at >= datetime({ begin }) AND t.created_at <= datetime({ end })
        RETURN collect(other.id)
        """, id=id, begin=begin, end=end).evaluate())

    users = Counter(graph.run("""
        MATCH (tag:Tag{id: {id}}) <-[:HAS_TAG]- (t:Tweet) -[:MENTIONS]-> (user:User)
        WHERE t.created_at >= datetime({ begin }) AND t.created_at <= datetime({ end })
        RETURN collect(user)
        """, id=id, begin=begin, end=end).evaluate())
    
    return render_template('tag.html', 
        tag=id, 
        tweets=tweets, 
        tags=tags.most_common(100),
        mentions=users.most_common(100),
        timeline={ 
            'xs': [str(d) for d, n in volume],
            'ys': [n for d, n in volume]
        })

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

    tags = graph.run("""
        MATCH (:Tweet{id: {id}}) -[:REFERS_TO*]- (ctx:Tweet) -[:HAS_TAG]-> (tag:Tag)
        RETURN collect(tag.id)
        """, id=id).evaluate()
    
    start = graph.run("MATCH(t:Tweet{id: {id}}) RETURN t.created_at", id=id).evaluate()
    durations = [t['dt'] - start for t in graph.run("""
        MATCH (:Tweet{id: {id}}) -[:REFERS_TO*]- (ctx:Tweet)
        RETURN ctx.created_at AS dt ORDER BY dt
        """, id=id)]
    hours = Counter([(d.days * 24 * 3600 + d.seconds) // 3600 for d in durations])
    xs = sorted(hours.keys())
    ys = [hours[x] for x in xs]

    usr_context = Counter([ctx['user'] for ctx in full_context]).most_common(100)

    return render_template('tweet.html', 
        tweet=tweet, 
        user=usr, 
        ctx=context, 
        full_ctx=full_context,
        user_ctx=usr_context,
        tags=Counter(tags).most_common(100),
        timeline={ 'xs': xs, 'ys': ys }
    )

@app.route("/users")
def trending_users():
    search = request.args.get("searchterm")

    result = graph.run("""
        CALL db.index.fulltext.queryNodes('users', { search }) YIELD node AS user, score
        OPTIONAL MATCH (user:User) -[:POSTS]-> (:Tweet) <-[:REFERS_TO]- (r:Tweet)
        RETURN user, count(r) AS qty, score ORDER BY qty DESCENDING, score DESCENDING
        LIMIT 1000
        """, search=search)

    return render_template('users.html', users=[ (t['user'], t['qty']) for t in result])

@app.route('/user/<id>')
def user_as_html(id):
    result = graph.run("MATCH (u:User{id: {id}}) RETURN u", id=id).evaluate()
    return render_template('user.html', user=result)

@app.route('/user/<id>/behaviour')
def user_behaviour(id):
    begin = request.args.get("begin", default="1970-01-01")
    end = request.args.get("end", default=dt.now().strftime("%Y-%m-%d"))

    result = [(r['type'], r['n']) for r in graph.run("""
        MATCH (u:User{id: {id}}) -[:POSTS]-> (t:Tweet)
        WHERE t.created_at >= datetime({begin}) AND t.created_at <= datetime({end})
        RETURN t.type AS type, count(t) AS n
        """, id=id, begin=begin, end=end)]

    return jsonify([{
        'labels': [t for t, n in result],
        'values': [n for t, n in result],
        'type': 'pie'
    }])

@app.route('/user/<id>/activity')
def user_activity(id):
    begin = request.args.get("begin", default="1970-01-01")
    end = request.args.get("end", default=dt.now().strftime("%Y-%m-%d"))

    posts = [(r['date'], r['n']) for r in graph.run("""
        MATCH (u:User{id: {id}}) -[:POSTS]-> (t:Tweet)
        WHERE t.created_at >= datetime({begin}) AND t.created_at <= datetime({end})
        RETURN date(t.created_at) AS date, count(t) AS n
        ORDER BY date
        """, id=id, begin=begin, end=end)]

    reactions = [(r['date'], r['n']) for r in graph.run("""
        MATCH (u:User{id: {id}}) -[:POSTS]-> (:Tweet) <-[:REFERS_TO*]- (o:Tweet)
        WHERE o.created_at >= datetime({begin}) AND o.created_at <= datetime({end})
        RETURN date(o.created_at) AS date, count(o) AS n
        ORDER BY date
        """, id=id, begin=begin, end=end)]

    return jsonify([{
        'x': [str(t) for t, n in posts],
        'y': [n for t, n in posts],
        'name': 'posts',
        'type': 'scatter'
    }, {
        'x': [str(t) for t, n in reactions],
        'y': [n for t, n in reactions],
        'name': 'reactions',
        'type': 'scatter'
    }])

@app.route('/user/<id>/retweeters')
def user_retweeters(id):
    begin = request.args.get("begin", default="1970-01-01")
    end = request.args.get("end", default=dt.now().strftime("%Y-%m-%d"))

    result = "".join([link(chip("@" + r['user']['screen_name'], data=r['n']), f"/user/{ r['user']['id'] }", classes=['filtered']) for r in graph.run("""
        MATCH (u:User{id: {id}}) -[:POSTS]-> (t:Tweet) <-[:REFERS_TO]- (:Tweet) <-[:POSTS]- (user:User)
        WHERE t.created_at >= datetime({begin}) AND t.created_at <= datetime({end})
        RETURN user, count(user) AS n
        ORDER BY n DESCENDING
        LIMIT 50
        """, id=id, begin=begin, end=end)])

    return result

@app.route('/user/<id>/tags')
def user_tags(id):
    begin = request.args.get("begin", default="1970-01-01")
    end = request.args.get("end", default=dt.now().strftime("%Y-%m-%d"))

    result = "".join([link(chip("#" + r['tag'], data=r['n']), f"/tag/{ r['tag'] }", classes=['filtered']) for r in graph.run("""
        MATCH (u:User{id: {id}}) -[:POSTS]-> (t:Tweet) -[:HAS_TAG]-> (tag:Tag)
        WHERE t.created_at >= datetime({begin}) AND t.created_at <= datetime({end})
        RETURN tag.id AS tag, count(tag) AS n
        ORDER BY n DESCENDING
        LIMIT 50
        """, id=id, begin=begin, end=end)])

    return result

@app.route('/user/<id>/tweets')
def user_tweets(id):
    begin = request.args.get("begin", default="1970-01-01")
    end = request.args.get("end", default=dt.now().strftime("%Y-%m-%d"))

    tweets = [{ 'tweet': r['t'], 'user': r['u'] } for r in graph.run("""
        MATCH (u:User{id: {id}}) -[:POSTS]-> (t:Tweet) <-[:REFERS_TO*]- (r:Tweet)
        WHERE t.type <> 'retweet' AND 
              t.created_at >= datetime({begin}) AND 
              t.created_at <= datetime({end})
        RETURN t, u, count(t) AS n
        ORDER BY n DESCENDING
        LIMIT 50
        """, id=id, begin=begin, end=end)]

    return tweetlist(tweets)

@app.route('/tweets')
def trending_tweets():

    searchterm = request.args.get("searchterm", default="n")
    begin = request.args.get("begin", default="1970-01-01")
    end = request.args.get("end", default=dt.now().strftime("%Y-%m-%d"))

    result = graph.run("""
        CALL db.index.fulltext.queryNodes('tweets', { searchterm }) YIELD node AS tweet, score
        WHERE tweet.type <> 'retweet' AND tweet.created_at >= datetime({ begin }) AND tweet.created_at <= datetime({ end })
        MATCH (r:Tweet) -[:REFERS_TO]- (tweet) <-[:POSTS]- (usr:User)
        RETURN tweet, usr, score, count(r) AS n ORDER BY n DESCENDING, tweet.created_at DESCENDING, score DESCENDING
        LIMIT 100
        """, searchterm=searchterm, begin=begin, end=end)

    timeline = [(t['date'], t['n']) for t in graph.run("""
        CALL db.index.fulltext.queryNodes('tweets', { searchterm }) YIELD node AS tweet, score
        WHERE tweet.created_at >= datetime({ begin }) AND tweet.created_at <= datetime({ end })
        RETURN date(tweet.created_at) AS date, count(tweet) AS n ORDER BY date
        """, searchterm=searchterm, begin=begin, end=end)]

    portion = [(t['type'], t['n']) for t in graph.run("""
        CALL db.index.fulltext.queryNodes('tweets', { searchterm }) YIELD node AS tweet, score
        WHERE tweet.created_at >= datetime({ begin }) AND tweet.created_at <= datetime({ end })
        RETURN tweet.type AS type, count(tweet) AS n ORDER BY type
        """, searchterm=searchterm, begin=begin, end=end)]

    rts = graph.run("""
        CALL db.index.fulltext.queryNodes('tweets', { searchterm }) YIELD node AS tweet, score
        MATCH (tweet:Tweet) <-[:REFERS_TO]- (rt:Tweet{type: 'retweet'})
        WHERE rt.created_at >= datetime({ begin }) AND rt.created_at <= datetime({ end })
        RETURN count(rt) AS n
        """, searchterm=searchterm, begin=begin, end=end).evaluate()

    return render_template('tweets.html', 
        tweets=[{'tweet': t['tweet'], 'user': t['usr'] } for t in result],
        plot={
            'xs': [str(d) for d, n in timeline],
            'ys': [n for d, n in timeline]
        },
        pie={
            'labels': ['retweet'] + [str(d) for d, n in portion],
            'values': [rts] + [n for d, n in portion]
        }
    )

@app.route('/search')
def search():
    entity = request.args.get("entity")
    if entity == "user":
        return redirect(url_for('trending_users'))
    else:
        return redirect(url_for('trending_tweets'))

def start(settings):
    global graph
    url = settings['neo4j_url']
    usr = settings['neo4j_usr']
    pwd = settings['neo4j_pwd']

    graph = Graph(url, auth=(usr, pwd))

    print(statics)
    print(templates)

    app.run()