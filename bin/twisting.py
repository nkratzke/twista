from twibot.analysis import TwibotGraph
from twibot import operator as on

import matplotlib.pyplot as plt
from matplotlib import gridspec
import argparse
import json

parser = argparse.ArgumentParser()
parser.add_argument('graphfile', type=argparse.FileType('rb'), help="Graph file to analyze")
parser.add_argument('-W', '--width', type=int, default=16, help='Width in inch of chart (default: 16)')
parser.add_argument('-H', '--height', type=int, default=9, help='Height in inch of chart (default: 9)')
parser.add_argument('--tweets', action="store_true", help="Shows distribution of statuses, replies, tweets and quotes.")
parser.add_argument('--answers', type=str, default="", help="Answers by politicians")
parser.add_argument('--title', type=str, default='', help='User defined title')
parser.add_argument('--tag-timeline', action="store_true", help="Display tag timelines (timeline chart)")
parser.add_argument('--top-tags', type=int, default=0, help="Display TOP n tags (default of n: 0, means not plotted)")
parser.add_argument('--top-mentions', type=int, default=0, help="Display TOP n user mentions (default of n: 0, means not plotted)")
parser.add_argument('--account-timeline', action="store_true", help="Display twitter account creation timelines (timeline chart)")
parser.add_argument('--histograms', action="store_true", help="Displays histogram of category retweeting fractions")
parser.add_argument('--supporters', action="store_true", help="Display relation of supporters (pie chart)")
parser.add_argument('--cloud', type=int, default=0, help="Display user mentions and hashtags of last n days")
parser.add_argument('--top-retweeter', type=int, default=0, help='Lists TOP-n retweeters')
parser.add_argument('--color', type=argparse.FileType('r'), help="Color codes")
args = parser.parse_args()
print(args)

if args.color:
    party_color = json.loads(args.color.read())

graph = TwibotGraph.load(args.graphfile)
print(graph.info())

command = ''

size = (args.width, args.height)

if args.answers:
    replies = graph.edges()\
        .filter(on.REPLY)\
        .filter(lambda r: r.src_node().initialtag)\
        .filter(lambda r: r.src_node().category() == args.answers)
    for reply in replies:
        print(reply.src_node().screenname + ": " + reply.text)
    exit(1)

if args.tweets:
    from twibot.visualization import pie_plot
    from twibot.visualization import line_plot
    from twibot.visualization import timeline_plot

    freqs = graph.edges().frequencies(on=lambda e: e.type)
    fig, ((ax1, ax2, ax3), (ax4, ax5, ax6)) = plt.subplots(2, 3, figsize=size)

    grouped = graph.edges().group(by=lambda e: e.type)

    hour_timelines = {}
    day_timelines = {}
    date_timelines = {}
    for type, tweets in grouped.items():
        hour_timelines[type] = tweets.frequencies(on=lambda e: e.created().hour)
        day_timelines[type] = tweets.frequencies(on=lambda e: e.created().isoweekday())
        date_timelines[type] = tweets.frequencies(on=lambda e: e.created().date())

    pie_plot(freqs, ax=ax1)
    line_plot(hour_timelines, ax=ax2, xaxis='Hour', yaxis='Tweets')
    line_plot(hour_timelines, ax=ax3, xaxis='Hour', norm=True)

    timeline_plot(date_timelines, ax=ax4, yaxis='Tweet')
    line_plot(day_timelines, ax=ax5, xaxis='Weekday', yaxis='Tweets')
    line_plot(day_timelines, ax=ax6, xaxis='Weekday', norm=True)
    plt.show()


if args.top_retweeter > 0:
    grouped = graph.edges().filter(lambda e: e.is_retweet()).group(by=lambda e: e.src_node().category())

    for party, edges in grouped.items():
        print(party)
        retweeters = edges.filter(lambda e: e.dest_node().category() == party).map(lambda e: e.dest_node())
        print(json.dumps(retweeters.frequencies(on=lambda n: n.screenname, top=args.top_retweeter), indent=3))

#
# Relation of party supporters
#
if args.supporters:
    from twibot.visualization import pie_plot
    from twibot.visualization import timeline_plot

    f, ((ax1, ax2), (ax3, ax4)) = plt.subplots(2, 2, figsize=size)

    allusers = graph.nodes().frequencies(on=lambda n: n.category())

    retweets = graph.edges().filter(lambda e: e.is_retweet())

    supporting_retweets = retweets.frequencies(on=lambda e: e.propagated())

    pie_plot(allusers, ax=ax1, colors=party_color, title='Anteil aller Retweeter (propagation result)')
    pie_plot(supporting_retweets, ax=ax3, colors=party_color, title='Anteil aller Retweets')

    contents = retweets.map(lambda t: t.propagated()).unique()

    hour_timelines = {}
    for content in contents:
        hour_timelines[content] = retweets.filter(lambda t: content == t.propagated()).frequencies(on=lambda t: t.created().date())
    hour_timelines['total'] = retweets.frequencies(on=lambda t: t.created().date())

    timeline_plot(hour_timelines, colors=party_color, ax=ax2, title='Absolute Anzahl an Retweets', yaxis="Retweets")
    del(hour_timelines['total'])

    timeline_plot(hour_timelines, colors=party_color, ax=ax4, norm=True, title='Relativer Anteil von Retweets', yaxis="Prozentualer Anteil")
    plt.show()


#
# User mentions and hashtags as word clouds of last n Hours
#
if args.cloud > 0:
    from twibot.visualization import word_cloud
    from twibot.visualization import pie_plot
    from twibot.visualization import timeline_plot

    f, ((ax1, ax2), (ax3, ax4)) = plt.subplots(2, 2, figsize=size)

    tweets = graph.edges().filter(on.LAST_DAYS(args.cloud))
    user_mentions = tweets.map(on.USER_MENTIONS).flatten().map(lambda um: "@%s" % um).frequencies()
    hashtags = tweets.map(on.HASHTAGS).flatten().map(lambda um: "#%s" % um).frequencies()

    top10_user_mentions = tweets.map(on.USER_MENTIONS).flatten().map(lambda um: "@%s" % um).frequencies(top=10)
    top10_hashtags = tweets.map(on.HASHTAGS).flatten().map(lambda um: "#%s" % um).frequencies(top=10)

    word_cloud(user_mentions, ax=ax1, title='Most frequently used user mentions (last %i days)' % args.cloud)
    word_cloud(hashtags, ax=ax3, title='Most frequently used hashtags (last %i days)' % args.cloud)
    pie_plot(top10_user_mentions, ax=ax2, title='Top 10 @user mentions')
    pie_plot(top10_hashtags, ax=ax4, title='Top 10 #hashtags')

    plt.show()

#
# Wenn heute Bundes-#tag-wahl wäre ...
#
if args.tag_timeline:
    from twibot.visualization import pie_plot
    from twibot.visualization import timeline_plot

    parties = {
        '#cdu/#csu': '#000000',
        '#spd': '#cc0000',
        '#grüne': '#006600',
        '#linke': '#ff0077',
        '#fdp': '#ffcc00',
        '#afd': '#0000ff'
    }

    tags = list([tag[1:] for tag in list(parties.keys())])

    f = plt.figure(figsize=size)
    f.suptitle(args.title)

    gs1, gs2 = gridspec.GridSpec(1, 2, width_ratios=[1, 2])
    ax1 = plt.subplot(gs1)
    ax2 = plt.subplot(gs2)

    tweets = {}
    tweets['#cdu/#csu'] = graph.edges().filter(lambda t: 'cdu' in t.hashtags or 'csu' in t.hashtags).count()
    tweets['#spd'] = graph.edges().filter(lambda t: 'spd' in t.hashtags).count()
    tweets['#grüne'] = graph.edges().filter(lambda t: 'grüne' in t.hashtags).count()
    tweets['#linke'] = graph.edges().filter(lambda t: 'linke' in t.hashtags).count()
    tweets['#fdp'] = graph.edges().filter(lambda t: 'fdp' in t.hashtags).count()
    tweets['#afd'] = graph.edges().filter(lambda t: 'afd' in t.hashtags).count()

    pie_plot(tweets, ax=ax1, colors=parties)

    timeline={}
    for tag in tags:
        timeline["#%s" % tag] = graph.edges().filter(lambda t: tag in t.hashtags).frequencies(on=on.DAY)
    timeline['#cdu/#csu'] = graph.edges().filter(lambda t: 'cdu' in t.hashtags or 'csu' in t.hashtags).frequencies(on=on.DAY)

    timeline_plot(timeline, ax=ax2, colors=parties, norm=True)

    plt.show()

#
# Plots TOP n tags
#
if args.top_tags > 0:

    from twibot.visualization import pie_plot
    from twibot.visualization import timeline_plot

    top_n_tags = graph.edges().map(on.HASHTAGS).flatten().frequencies(top=args.top_tags)

    top_n_timelines = {}
    for tag in list(top_n_tags.keys()):
        top_n_timelines[tag] = graph.edges().filter(lambda e: tag in e.hashtags).frequencies(on=on.DAY)

    f = plt.figure(figsize=size)
    f.suptitle("TOP %i #Tags" % args.top_tags)

    gs1, gs2 = gridspec.GridSpec(1, 2, width_ratios=[1, 2])
    ax1 = plt.subplot(gs1)
    ax2 = plt.subplot(gs2)

    pie_plot(top_n_tags, ax=ax1)
    timeline_plot(top_n_timelines, ax=ax2, title="TOP %i Tags im Verlaufe der Zeit" % args.top_tags, yaxis="Tweets containing tag")

    plt.show()

#
# Plots TOP n user mentions
#
if args.top_mentions > 0:

    from twibot.visualization import pie_plot
    from twibot.visualization import timeline_plot

    top10_mentions = graph.edges().map(lambda e: e.usermentions).flatten().frequencies(top=args.top_mentions)

    top_n_timelines = {}
    for mention in list(top10_mentions.keys()):
        top_n_timelines[mention] = graph.edges().filter(lambda e: mention in e.usermentions).frequencies(on=lambda e: e.created().date())

    f = plt.figure(figsize=size)
    f.suptitle("TOP %i @User Mentions" % args.top_mentions)

    gs1, gs2 = gridspec.GridSpec(1, 2, width_ratios=[1, 2])
    ax1 = plt.subplot(gs1)
    ax2 = plt.subplot(gs2)

    pie_plot(top10_mentions, ax=ax1)
    timeline_plot(top_n_timelines, ax=ax2, title="TOP %i User Mentions im Verlaufe der Zeit" % args.top_tags, yaxis="Tweets containing @user")

    plt.show()


#
# Plot supporting twitter account over years
#
if args.account_timeline:
    from twibot.visualization import line_plot
    from datetime import datetime
    from dateutil import relativedelta

    fig = plt.figure(figsize=size)

    grouped = graph.nodes().filter(lambda e: e.created().year > 2000).group(by=lambda n: n.category())

    months = lambda d1, d2: (12 * d2.year + d2.month) - (12 * d1.year + d1.month)

    users = {}
    now = datetime.now()
    for party, accounts in grouped.items():
        users[party] = accounts.frequencies(on=lambda n: months(n.created(), now))

    del(users['unknown'])
    del(users['inconsistent'])

    line_plot(
        users,
        ax = fig.gca(),
        colors=party_color,
        yaxis="Created Twitter accounts (absolute numbers)",
        title="Retweeting accounts created month ago",
        x_invert=True,
        norm=False
    )
    fig.gca().set_xlim(1, 48)
    fig.gca().invert_xaxis()

    plt.show()

if args.histograms:
    categories = graph.nodes().map(lambda n: n.tag).flatten().unique()

    n = categories.count()
    get = lambda c, n: n.categoryp()[c] if c in n.categoryp() else 0

    fig, axes = plt.subplots(n, 1, figsize=size, sharex=True)
    fig.suptitle("Histogram Verbreitungshäufigkeiten")
    i = 0
    for c in categories:
        data = graph.nodes().map(lambda n: get(c, n)).filter(lambda v: v > 0)
        axes[i].hist(data, 5, orientation='horizontal', rwidth=0.75, normed=1, color=party_color[c])
        axes[i].set_yticks((0.1, 0.3, 0.5, 0.7, 0.9))
        axes[i].set_yticklabels(
            ['Selten (0 - 20%)', 'Gelegentlich (20% - 40%)', 'Wechselnd (40% - 60%)', 'Überwiegend (60% - 80%)',
             'Ausschließlich (80% - 100%)'])
        i += 1

    plt.show()