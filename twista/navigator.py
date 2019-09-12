from flask import Flask, escape, request, Response, render_template, redirect, url_for
from py2neo import Graph
from collections import Counter
from datetime import datetime as dt
from datetime import timedelta
import json
import os
from dateutil import parser

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

@app.template_filter()
def datetime(dt):
    return parser.parse(str(dt)).strftime("%Y-%m-%d %H:%M:%S")

@app.route('/')
def hello():
    return redirect(url_for('/tweets/'))

@app.route('/tags/')
def trending_tags():
    result = [(r['tag'], r['n']) for r in graph.run("""
        MATCH (tag:Tag) <-[:HAS_TAG]- (t:Tweet)
        RETURN tag.id AS tag, count(t) AS n
        ORDER BY n DESCENDING LIMIT 100
        """)]

    tags = [t for t, n in result[0:10]]
    timelines = graph.run("""
        UNWIND {tags} AS tg
        MATCH (t:Tweet) -[:HAS_TAG]-> (:Tag{id: tg})
        RETURN tg, date(t.created_at) as date, count(t) as n
        ORDER BY date
        """, tags=tags).data()
    data = { t: { 
            'xs': [str(e['date']) for e in timelines if e['tg'] == t],
            'ys': [e['n'] for e in timelines if e['tg'] == t]
        } for t in tags }

    return render_template('tags.html', tags=result, timelines=data)

@app.route('/tag/<id>')
def tweets_for_tag(id):

    volume = [(r['date'], r['n']) for r in graph.run("""
        MATCH (:Tag{id: {id}}) <-[:HAS_TAG]- (t:Tweet)
        WHERE t.created_at > datetime("2019-04-01")
        RETURN date(t.created_at) AS date, count(t) as n ORDER BY date
        """,id=id)]

    tweets = [{ 'tweet': tweet['t'], 'user': tweet['u'] } for tweet in graph.run("""
        MATCH (tag:Tag{id: {id}}) <-[:HAS_TAG]- (t:Tweet) <-[:POSTS]- (u:User)
        WHERE t.type <> 'retweet'
        RETURN t, u
        ORDER BY t.created_at DESCENDING
        LIMIT 100
        """, id=id)]

    tags = Counter(graph.run("""
        MATCH (tag:Tag{id: {id}}) <-[:HAS_TAG]- (t:Tweet) -[:HAS_TAG]-> (other:Tag)
        WHERE tag <> other
        RETURN collect(other.id)
        """, id=id).evaluate())

    users = Counter(graph.run("""
        MATCH (tag:Tag{id: {id}}) <-[:HAS_TAG]- (t:Tweet) -[:MENTIONS]-> (user:User)
        RETURN collect(user)
        """, id=id).evaluate())
    
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
    since = dt.utcnow() - timedelta(hours=72)
    print(since)
    result = [(r['u'], r['n']) for r in graph.run("""
        MATCH (u:User) <-[:MENTIONS]- (t:Tweet)
        WHERE t.created_at > datetime({ since })
        RETURN u, count(t) AS n
        ORDER BY n DESCENDING LIMIT 100
        """, since = since)]

    return render_template('users.html', users=result)

@app.route("/users/search")
def users_search():
    search_arg = request.args.get("search")

    if not search_arg:
        return render_template('users.html', users=[])

    result = graph.run("""
        CALL db.index.fulltext.queryNodes('users', { search }) YIELD node AS user, score
        OPTIONAL MATCH (user:User) -[:POSTS]-> (:Tweet) <-[:REFERS_TO]- (r:Tweet)
        RETURN user, count(r) AS qty, score ORDER BY qty DESCENDING, score DESCENDING
        LIMIT 1000
    """, search=search_arg)
    return render_template('users.html', users=[ (t['user'], t['qty']) for t in result])

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

    volume = [(r['date'], r['n']) for r in graph.run("""
        MATCH (:User{id: {id}}) -[:POSTS]-> (t:Tweet)
        WHERE t.created_at > datetime("2019-04-01")
        RETURN date(t.created_at) AS date, count(t) as n ORDER BY date
        """, id=id)]

    reactions = [(r['date'], r['n']) for r in graph.run("""
        MATCH (:User{id: {id}}) -[:POSTS]-> (:Tweet) <-[:REFERS_TO*]- (r:Tweet)
        WHERE r.created_at > datetime("2019-04-01")
        RETURN date(r.created_at) as date, count(r) as n ORDER BY date
        """, id=id)]

    behaviour = [(r['type'], r['n']) for r in graph.run("""
        MATCH (u:User{id: {id}}) -[:POSTS]-> (t:Tweet) 
        RETURN t.type AS type, count(t) AS n
        ORDER BY type
        """, id=id)]

    return render_template('user.html', 
        user=result, 
        tags=Counter(tags).most_common(100),
        retweeters=Counter(retweeters).most_common(100),
        actions = {
            'xs': [str(d) for d, n in volume],
            'ys': [n for d, n in volume]
        },
        reactions = {
            'xs': [str(d) for d, n in reactions],
            'ys': [n for d, n in reactions]
        },
        behaviour = {
            'types': [t for t, n in behaviour],
            'n': [n for t, n in behaviour]
        }
    )

@app.route('/tweets/')
def trending_tweets():
    since = dt.utcnow() - timedelta(hours=72)

    result = [{ 'tweet': r['t'], 'user': r['u'] } for r in graph.run("""
        MATCH (u:User) -[:POSTS]-> (t:Tweet) <-[:REFERS_TO*]- (r:Tweet)
        WHERE t.created_at > datetime({ since })
        RETURN u, t, count(r) AS n
        ORDER BY n DESCENDING LIMIT 100
        """, since = since)]

    return render_template('tweets.html', tweets=result)


@app.route('/tweets/search')
def search():
    search_arg = request.args.get("search")

    if not search_arg:
        return render_template('tweets.html', tweets=[])

    since = (datetime.utcnow() - timedelta(days=7)).strftime("%Y-%m-%d")
    result = graph.run("""
        CALL db.index.fulltext.queryNodes('tweets', { search }) YIELD node AS tweet, score
        WHERE tweet.type <> 'retweet' AND tweet.retweets IS NOT NULL AND tweet.created_at > datetime({ since })
        MATCH (r:Tweet) -[:REFERS_TO]- (tweet) <-[:POSTS]- (usr:User)
        RETURN tweet, usr, score, count(r) AS n ORDER BY n DESCENDING, tweet.created_at DESCENDING, score DESCENDING
        LIMIT 100
    """, search=search_arg, since = since)
    return render_template('tweets.html', tweets=[{'tweet': t['tweet'], 'user': t['usr'] } for t in result])

def start(settings):
    global graph
    url = settings['neo4j_url']
    usr = settings['neo4j_usr']
    pwd = settings['neo4j_pwd']

    graph = Graph(url, auth=(usr, pwd))

    print(statics)
    print(templates)

    app.run()