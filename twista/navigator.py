from flask import Flask, escape, request, Response, render_template, redirect, url_for, jsonify
from py2neo import Graph
from collections import Counter
from datetime import datetime as dt
from datetime import timedelta
import json
import os
from dateutil import parser, relativedelta
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

@app.template_filter()
def link(content, url, classes=[]):
    cs = " ".join(classes)
    return f"<a class='{ cs }' href='{ url }'>{ content }</a>"

@app.template_filter()
def datetime(dt):
    return parser.parse(str(dt)).strftime("%Y-%m-%d %H:%M:%S")

def filter(args):
    begin = args.get("begin", default="1970-01-01")
    end = args.get("end", default=dt.now().strftime("%Y-%m-%d"))
    if begin == "null":
        begin = "1970-01-01"
    if end == "null":
        end = dt.now().strftime("%Y-%m-%d")
    return (begin, end)

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/tag/<id>')
def tag(id):
    (begin, end) = filter(request.args)    
    return render_template('tag.html', tag=id)

@app.route('/tag/<id>/volume')
def tag_activity(id):
    (begin, end) = filter(request.args)    

    volume = [(r['date'], r['n']) for r in graph.run("""
        MATCH (tag:Tag) <-[:HAS_TAG]- (t:Tweet)
        WHERE toUpper(tag.id) = toUpper({ id }) AND
              t.created_at >= datetime({ begin }) AND
              t.created_at <= datetime({ end })
        RETURN date(t.created_at) AS date, count(t) AS n
        ORDER BY date
        """, id=id, begin=begin, end=end)]

    return jsonify([{
            'x': [str(d) for d, n in volume],
            'y': [n for d, n in volume],
            'type': 'scatter',
            'name': 'posts'
        }
    ])

@app.route('/tag/<id>/behaviour')
def tag_behaviour(id):
    (begin, end) = filter(request.args)    

    volume = [(r['type'], r['n']) for r in graph.run("""
        MATCH (tag:Tag) <-[:HAS_TAG]- (t:Tweet)
        WHERE toUpper(tag.id) = toUpper({ id }) AND
              t.created_at >= datetime({ begin }) AND
              t.created_at <= datetime({ end })
        RETURN t.type AS type, count(t) AS n
        ORDER BY type
        """, id=id, begin=begin, end=end)]

    return jsonify([{
            'labels': [t for t, n in volume],
            'values': [n for d, n in volume],
            'type': 'pie'
        }
    ])

@app.route('/tag/<id>/tags')
def tag_correlated_tags(id):
    (begin, end) = filter(request.args)    

    tags = [(r['tag'], r['n']) for r in graph.run("""
        MATCH (tag:Tag) <-[:HAS_TAG]- (t:Tweet) -[:HAS_TAG]-> (other:Tag)
        WHERE toUpper(tag.id) = toUpper({ id }) AND
            t.created_at >= datetime({ begin }) AND
            t.created_at <= datetime({ end }) AND
            tag <> other
        RETURN toUpper(other.id) AS tag, count(other) AS n
        ORDER BY n DESCENDING
        LIMIT 50
        """, id=id, begin=begin, end=end)]

    return " ".join(
        [link(chip("#" + tag, data=n), f"/tag/{tag}", classes=['filtered']) for tag, n in tags]
    )

@app.route('/tag/<id>/mentioned_users')
def tag_correlated_users(id):
    (begin, end) = filter(request.args)    

    users = [(r['user'], r['n']) for r in graph.run("""
        MATCH (tag:Tag) <-[:HAS_TAG]- (t:Tweet) -[m:MENTIONS]-> (u:User)
        WHERE toUpper(tag.id) = toUpper({ id }) AND
              t.created_at >= datetime({ begin }) AND
              t.created_at <= datetime({ end })
        RETURN u AS user, count(u) AS n
        ORDER BY n DESCENDING
        LIMIT 50
        """, id=id, begin=begin, end=end)]

    return "\n".join(
        [link(chip("@" + user['screen_name'], data=n), f"/user/{ user['id'] }", classes=['filtered']) for user, n in users]
    )

@app.route('/tag/<id>/posting_users')
def tag_posting_users(id):
    (begin, end) = filter(request.args)    

    users = [(r['user'], r['n']) for r in graph.run("""
        MATCH (tag:Tag) <-[:HAS_TAG]- (t:Tweet) <-[:POSTS]- (u:User)
        WHERE toUpper(tag.id) = toUpper({ id }) AND
              t.created_at >= datetime({ begin }) AND
              t.created_at <= datetime({ end })
        RETURN u AS user, count(u) AS n
        ORDER BY n DESCENDING
        LIMIT 50
        """, id=id, begin=begin, end=end)]

    return "\n".join(
        [link(chip("@" + user['screen_name'], data=n), f"/user/{ user['id'] }", classes=['filtered']) for user, n in users]
    )

@app.route('/tweet/<id>')
def tweet(id):
    (begin, end) = filter(request.args)    

    result = graph.run("MATCH (t:Tweet{id: {id}}) <-[:POSTS]- (u:User) RETURN t, u", id=id).data()
    tweet = result[0]['t']
    usr = result[0]['u']

    context = [{ 'tweet': ctx['tweet'], 'user': ctx['usr'] } for ctx in graph.run("""
        MATCH (:Tweet{id: {id}}) -[:REFERS_TO*]-> (tweet:Tweet) <-[:POSTS]- (usr:User)
        WHERE tweet.created_at >= datetime({ begin }) AND
              tweet.created_at <= datetime({ end })
        RETURN tweet, usr
        ORDER BY tweet.created_at DESCENDING
        """, id=id, begin=begin, end=end)]
    
    return render_template('tweet.html', 
        tweet=tweet, 
        user=usr, 
        ctx=context
    )

@app.route('/tweet/<id>/interactions')
def tweet_interactions(id):
    (begin, end) = filter(request.args)    

    tweet = graph.run("MATCH (t:Tweet{id: { id }}) RETURN t", id=id).evaluate()

    volume = [(r['date'], r['hour'], r['n']) for r in graph.run("""
        MATCH (:Tweet{id: { id }}) -[:REFERS_TO*]- (t:Tweet)
        WHERE t.created_at >= datetime({ begin }) AND
              t.created_at <= datetime({ end })
        RETURN date(t.created_at) AS date, t.created_at.hour AS hour, count(t) AS n
        ORDER BY date, hour
        """, id=id, begin=begin, end=end)]

    d0 = dt(tweet['created_at'].year, tweet['created_at'].month, tweet['created_at'].day, tweet['created_at'].hour)

    return jsonify([{
        'x': [str(dt(d.year, d.month, d.day, h)) for d, h, n in volume],
        'y': [n for d, h, n in volume],
        'type': 'scatter',
        'name': 'Interactions'
    }, {
        'x': [str(d0), str(d0)],
        'y': [0, max([n for d, h, n in volume], default=0)],
        'type': 'scatter',
        'name': 'Current tweet'
    }])

@app.route('/tweet/<id>/interaction-types')
def tweet_interaction_types(id):
    (begin, end) = filter(request.args)    

    volume = [(r['type'], r['n']) for r in graph.run("""
        MATCH (:Tweet{id: { id }}) -[:REFERS_TO*]- (t:Tweet)
        WHERE t.created_at >= datetime({ begin }) AND
              t.created_at <= datetime({ end })
        RETURN t.type AS type, count(t) AS n
        ORDER BY type
        """, id=id, begin=begin, end=end)]

    return jsonify([{
        'labels': [t for t, n in volume],
        'values': [n for t, n in volume],
        'type': 'pie',
    }])

@app.route('/tweet/<id>/tags')
def tweet_tags(id):
    (begin, end) = filter(request.args)    

    tags = [(r['tag'], r['n']) for r in graph.run("""
        MATCH (:Tweet{id: { id }}) -[:REFERS_TO*]- (t:Tweet) -[:HAS_TAG]-> (tag:Tag)
        WHERE t.created_at >= datetime({ begin }) AND
              t.created_at <= datetime({ end })
        RETURN tag.id AS tag, count(tag) AS n
        ORDER BY n DESCENDING
        LIMIT 50
        """, id=id, begin=begin, end=end)]

    return " ".join(
        [link(chip("#" + tag, data=n), f"/tag/{ tag }", classes=['filtered']) for tag, n in tags]
    )

@app.route('/tweet/<id>/users')
def tweet_users(id):
    (begin, end) = filter(request.args)    

    users = [(r['user'], r['n']) for r in graph.run("""
        MATCH (:Tweet{id: { id }}) -[:REFERS_TO*]- (t:Tweet) <-[:POSTS]- (u:User)
        WHERE t.created_at >= datetime({ begin }) AND
              t.created_at <= datetime({ end })
        RETURN u AS user, count(u) AS n
        ORDER BY n DESCENDING
        LIMIT 50
        """, id=id, begin=begin, end=end)]

    return " ".join(
        [link(chip("@" + usr['screen_name'], data=n), f"/user/{ usr['id'] }", classes=['filtered']) for usr, n in users]
    )

@app.route('/tweet/<id>/tweets')
def tweet_related_tweets(id):
    (begin, end) = filter(request.args)    

    tweets = [{ 'tweet': r['t'], 'user': r['u'] } for r in graph.run("""
        MATCH (:Tweet{id: { id }}) -[:REFERS_TO*]- (t:Tweet) <-[:POSTS]- (u:User)
        WHERE t.created_at >= datetime({ begin }) AND
              t.created_at <= datetime({ end })
        RETURN t, u
        ORDER BY t.created_at DESCENDING
        """, id=id, begin=begin, end=end)]

    return tweetlist(tweets)

@app.route('/user/<id>')
def user_as_html(id):
    result = graph.run("MATCH (u:User{id: {id}}) RETURN u", id=id).evaluate()
    return render_template('user.html', user=result)

@app.route('/user/<id>/behaviour')
def user_behaviour(id):
    (begin, end) = filter(request.args)    

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
    (begin, end) = filter(request.args)    

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

    mentions = [(r['date'], r['n']) for r in graph.run("""
        MATCH (u:User{id: {id}}) <-[:MENTIONS]- (t:Tweet)
        WHERE t.created_at >= datetime({begin}) AND t.created_at <= datetime({end})
        RETURN date(t.created_at) AS date, count(t) AS n
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
    }, {
        'x': [str(t) for t, n in mentions],
        'y': [n for t, n in mentions],
        'name': 'mentions',
        'type': 'scatter'
    }])

@app.route('/user/<id>/interactors')
def user_interactors(id):
    (begin, end) = filter(request.args)    
    action = request.args.get("type", default="retweet")

    result = " ".join([link(chip("@" + r['user']['screen_name'], data=r['n']), f"/user/{ r['user']['id'] }", classes=['filtered']) for r in graph.run("""
        MATCH (u:User{id: {id}}) -[:POSTS]-> (:Tweet) <-[:REFERS_TO]- (t:Tweet{type: {action}}) <-[:POSTS]- (user:User)
        WHERE t.created_at >= datetime({begin}) AND t.created_at <= datetime({end}) AND user <> u
        RETURN user, count(user) AS n
        ORDER BY n DESCENDING
        LIMIT 50
        """, id=id, begin=begin, end=end, action=action)])

    return result

@app.route('/user/<id>/tags')
def user_tags(id):
    (begin, end) = filter(request.args)    

    result = " ".join([link(chip("#" + r['tag'], data=r['n']), f"/tag/{ r['tag'] }", classes=['filtered']) for r in graph.run("""
        MATCH (u:User{id: {id}}) -[:POSTS]-> (t:Tweet) -[:HAS_TAG]-> (tag:Tag)
        WHERE t.created_at >= datetime({begin}) AND t.created_at <= datetime({end})
        RETURN tag.id AS tag, count(tag) AS n
        ORDER BY n DESCENDING
        LIMIT 50
        """, id=id, begin=begin, end=end)])

    return result

@app.route('/user/<id>/contents')
def user_posts(id):
    of = request.args.get("of")

    tweets = [{ 'tweet': r['t'], 'user': r['u'] } for r in graph.run("""
        MATCH (u:User{id: {id}}) -[:POSTS]-> (t:Tweet)
        WHERE date(t.created_at) = date({of})
        RETURN t, u, t.favourites AS n
        ORDER BY n DESCENDING
        """, id=id, of=of)]

    print(tweets)

    return tweetlist(tweets)

@app.route('/user/<id>/info')
def user_info(id):
    (begin, end) = filter(request.args)    

    user = graph.run("MATCH (u:User{id: {id}}) RETURN u", id=id).evaluate()
    return render_template('user_info.html', user=user)

@app.route('/user/<id>/punchcard')
def user_punchcard(id):
    (begin, end) = filter(request.args)

    pc = { d: { h: 0 for h in range(24) } for d in range(1, 8) }
    for r in graph.run("""
        MATCH (u:User{id: {id}}) -[:POSTS]-> (t:Tweet)
        WHERE t.created_at >= datetime({begin}) AND t.created_at <= datetime({end})
        RETURN t.created_at.weekday AS day, t.created_at.hour AS hour, count(t) AS n
        """, id=id, begin=begin, end=end):
        pc[r['day']][r['hour']] = r['n']

    weekdays =['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun']
    hours = range(24)

    data = [{
        'x': [f"{h}h" for h in hours],
        'y': weekdays,
        'z': [[pc[d][h] for h in hours] for d in range(1, 8)],
        'colorscale': [
            ['0.0', '#3F51B600'],
            ['0.1', '#3F51B611'],
            ['0.2', '#3F51B622'],
            ['0.3', '#3F51B633'],
            ['0.4', '#3F51B644'],
            ['0.5', '#3F51B655'],
            ['0.6', '#3F51B677'],
            ['0.7', '#3F51B699'],
            ['0.8', '#3F51B6BB'],
            ['0.9', '#3F51B6DD'],
            ['1.0', '#3F51B6FF']
        ],
        'type': 'heatmap'
    }]

    return jsonify(data)

@app.route('/user/<id>/network')
def user_network(id):
    (begin, end) = filter(request.args)    

    user = graph.run("MATCH (u:User{id: {id}}) RETURN u", id=id).evaluate()

    new = set([user['id']])
    process = new.copy()
    scanned = new.copy()

    retweeters = []
    for n in [50, 5, 5]:
        retweeters.extend([(r['u'], r['rt'], r['n']) for r in graph.run("""
            UNWIND {uids} AS uid
            MATCH (u:User{id: uid}) -[:POSTS]-> (:Tweet) <-[:REFERS_TO]- (t:Tweet{type: 'retweet'}) <-[:POSTS]- (rt:User)
            WHERE t.created_at >= datetime({ begin }) AND t.created_at <= datetime({ end }) AND u <> rt
            RETURN u, rt, count(rt) AS n
            ORDER BY n DESCENDING
            LIMIT {n}
            """, uids=list(process), begin=begin, end=end, n=len(new) * n)])
        new = set([r['id'] for u, r, _ in retweeters])
        process = new - scanned
        scanned = scanned.union(new)

    nodes = [u for u, _, _ in retweeters]
    nodes.extend([rt for _, rt, _ in retweeters])
    mark = lambda n: 'start' if (n['id'] == user['id']) else 'follow'
    network = { 
        'nodes': [{ 'data': { 'id': u['id'], 'screen_name': "@" + u['screen_name'], 'select': mark(u) }} for u in set(nodes)], 
        'edges': [{ 'data': { 'source': u['id'], 'target': rt['id'], 'directed': True, 'qty': n }} for u, rt, n in retweeters] 
    }

    return jsonify(network)
    # return render_template('network.js', user=user, elements=json.dumps(network))

@app.route('/tweets/volume')
def tweets_volume():
    (begin, end) = filter(request.args)    

    tweets = [(r['date'], r['n']) for r in graph.run("""
        MATCH (t:Tweet)
        WHERE t.created_at >= datetime({ begin }) AND
              t.created_at <= datetime({ end })
        RETURN date(t.created_at) AS date, count(t) AS n
        """, begin=begin, end=end)]

    users = [(r['date'], r['n']) for r in graph.run("""
        MATCH (t:Tweet) <-[:POSTS]- (u:User)
        WHERE t.created_at >= datetime({ begin }) AND
              t.created_at <= datetime({ end })
        RETURN date(t.created_at) AS date, count(distinct(u)) AS n
        """, begin=begin, end=end)]

    return jsonify([
        {
            'x': [str(d) for d, n in tweets],
            'y': [n for d, n in tweets],
            'type': 'scatter',
            'name': 'postings'
        }, {
            'x': [str(d) for d, n in users],
            'y': [n for d, n in users],
            'type': 'scatter',
            'name': 'active unique users'
        }
    ])

@app.route('/tweets/tags')
def tweets_tags_volume():
    (begin, end) = filter(request.args)    

    volume = [(r['tag'], r['n']) for r in graph.run("""
        MATCH (t:Tweet) -[:HAS_TAG]-> (tag:Tag)
        WHERE t.created_at >= datetime({ begin }) AND
              t.created_at <= datetime({ end })
        RETURN tag.id AS tag, count(tag) AS n
        ORDER BY n DESCENDING
        LIMIT 50
        """, begin=begin, end=end)]

    return " ".join(
        [link(chip("#" + tag, data=n), f"/tag/{tag}", classes=["filtered"]) for tag, n in volume]
    )

@app.route('/tweets/posting-users')
def tweets_most_posting_users():
    (begin, end) = filter(request.args)    

    volume = [(r['u'], r['n']) for r in graph.run("""
        MATCH (t:Tweet) <-[:POSTS]- (u:User)
        WHERE t.created_at >= datetime({ begin }) AND
              t.created_at <= datetime({ end })
        RETURN u, count(t) AS n
        ORDER BY n DESCENDING
        LIMIT 50
        """, begin=begin, end=end)]

    return " ".join(
        [link(chip("@" + usr['screen_name'], data=n), f"/user/{usr['id']}", classes=["filtered"]) for usr, n in volume]
    )

@app.route('/tweets/mentioned-users')
def tweets_most_mentioned_users():
    (begin, end) = filter(request.args)    

    volume = [(r['u'], r['n']) for r in graph.run("""
        MATCH (t:Tweet) -[:MENTIONS]-> (u:User)
        WHERE t.created_at >= datetime({ begin }) AND
              t.created_at <= datetime({ end })
        RETURN u, count(t) AS n
        ORDER BY n DESCENDING
        LIMIT 50
        """, begin=begin, end=end)]

    return " ".join(
        [link(chip("@" + usr['screen_name'], data=n), f"/user/{usr['id']}", classes=["filtered"]) for usr, n in volume]
    )

@app.route('/tweets/types')
def tweets_type_volume():
    (begin, end) = filter(request.args)    

    volume = [(r['type'], r['n']) for r in graph.run("""
        MATCH (t:Tweet)
        WHERE t.created_at >= datetime({ begin }) AND
              t.created_at <= datetime({ end })
        RETURN t.type AS type, count(t) AS n
        ORDER BY type
        """, begin=begin, end=end)]

    return jsonify([{
        'labels': [t for t, n in volume],
        'values': [n for t, n in volume],
        'type': 'pie'
    }])

@app.route('/search')
def search():
    (begin, end) = filter(request.args)    
    search = request.args.get("searchterm", default="")
    entity = request.args.get("type", default="users")

    return render_template('search.html', searchterm=search, type=entity)

@app.route('/search/tweet')
def search_tweets():
    search = request.args.get("searchterm", default="")
    return f"Searching for '{search}' in tweets works basically"

@app.route('/search/user')
def search_users():
    search = request.args.get("searchterm", default="")

    hits = [r['user'] for r in graph.run("""
        CALL db.index.fulltext.queryNodes('users', { search }) YIELD node AS user, score
        MATCH (user:User) -[:POSTS]-> (t:Tweet) <-[:REFERS_TO]- (r:Tweet)
        RETURN user, count(r) AS i
        ORDER BY i DESCENDING
        LIMIT 1000
        """, search=search)]

    return render_template('users_list.html', users=hits, search=search)   


@app.route('/retweets/')
def get_retweets():
    (begin, end) = filter(request.args)    
    sid = request.args.get("source")
    tid = request.args.get("target")

    result = [{ 'tweet': r['x'], 'user': r['u'] } for r in graph.run("""
        MATCH (u:User{id: {sid}}) -[:POSTS]-> (x:Tweet) <-[:REFERS_TO]- (t:Tweet{type:'retweet'}) <-[:POSTS]- (v:User{id:{tid}})
        WHERE t.created_at >= datetime({begin}) AND t.created_at <= datetime({end})
        RETURN x, u
        ORDER BY x.created_at
    """, sid=sid, tid=tid, begin=begin, end=end)]

    return render_template('tweet_list.html', tweets=result)

@app.route('/stats/postings')
def stats_for_postings():
    (begin, end) = filter(request.args)    

    N = 10000
    result = [(r['duration'], r['n']) for r in graph.run("""
        MATCH (u:User) -[:POSTS]-> (t:Tweet)
        WHERE t.created_at >= datetime({begin}) AND 
              t.created_at <= datetime({end})
        RETURN duration.inDays(datetime({begin}), datetime({end})) AS duration, count(t) AS n
        LIMIT { N }
        """, begin=begin, end=end, N=N)]

    r = Counter([d.days // n for d, n in result])
    return jsonify({ f: n / N * 100 for f, n in r.items() })
    

def start(settings):
    global graph
    url = settings['neo4j_url']
    usr = settings['neo4j_usr']
    pwd = settings['neo4j_pwd']
    graph = Graph(url, auth=(usr, pwd))
    app.run()