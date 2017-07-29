from datetime import date
from datetime import timedelta

#
# Predicates to select specific edges (intended to be used with filter)
#
STATUS = lambda edge: edge.is_status()
RETWEET = lambda edge: edge.is_retweet()
REPLY = lambda edge: edge.is_reply()
QUOTE = lambda edge: edge.is_quote()

LAST_HOURS = lambda n: lambda edge: edge.created().date() >= date.today() - timedelta(hours=n)
LAST_DAYS = lambda n: lambda edge: edge.created().date() >= date.today() - timedelta(days=n)

#
# Functions to extract data from nodes
#

#
# Functions to extract data from edges (intended to be used with mapping)
#
USER_MENTIONS = lambda edge: edge.usermentions
HASHTAGS = lambda edge: edge.hashtags
DAY = lambda edge: edge.created().date()


def TYPE (tweet):
    if tweet.is_status(): return 'status'
    if tweet.is_quote(): return 'quote'
    if tweet.is_retweet(): return 'retweet'
    if tweet.is_reply(): return 'reply'
    return 'unknown'
