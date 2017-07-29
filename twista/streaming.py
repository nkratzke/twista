import tweepy
import uuid
import bs4
import requests
import re
import json
from urllib.parse import urljoin

from twista.analysis import Tweet

JSON_INDENT = 3
CHUNK_SIZE = 1000


class StreamListener(tweepy.StreamListener):

    def __init__(self):
        self.tweets = []
        self.chunk_file = self.new_chunk()

    def new_chunk(self):
        chunk = "chunk-" + str(uuid.uuid4()) + ".json"
        print("New chunk " + chunk)
        return chunk

    def on_data(self, raw_data):
        try:
            data = json.loads(raw_data)
            tweet = Tweet(data)

            if not tweet.is_deleted() and not tweet.is_withheld():
                print(tweet.user().screen_name() + ": " + tweet.text())
                self.tweets.append(data)
                fo = open(self.chunk_file, "w")
                fo.write(json.dumps(self.tweets, indent=JSON_INDENT))
                fo.close()

            if len(self.tweets) >= CHUNK_SIZE:
                print("%i tweets collected" % CHUNK_SIZE)
                self.chunk_file = self.new_chunk()
                self.tweets = []

        except Exception as ex:
            print(ex)
            print("Error while parsing: " + raw_data)


def crawl_for_screennames(url):
    print("Crawling " + url)
    screennames = []
    res = requests.get(url)
    soup = bs4.BeautifulSoup(res.text, 'html5lib')
    for link in soup.select('a[href^=http://twitter.com/], a[href^=https://twitter.com/], a[href^=http://www.twitter.com/], a[href^=https://www.twitter.com/]'):
        href = link.get('href')
        href = href.replace('https://', '')
        href = href.replace('http://', '')
        href = href.replace('www.twitter.com/', '')
        href = href.replace('twitter.com/', '')

        screenname = re.findall(r"[A-Za-z0-9_]+", href)[0]
        if not screenname in ['flickr', 'signup', 'privacy', 'share', 'home']:
            screennames.append(screenname)
    return screennames

visited = []

def crawl(url, n=0):
    if url in visited:
        print("Skipping " + url + ": Already visited.")
        return []

    screennames = crawl_for_screennames(url)
    visited.append(url)
    if n == 0:
        return list(set(screennames))

    res = requests.get(url)
    soup = bs4.BeautifulSoup(res.text, 'html5lib')
    for link in soup.select('a[href]'):
        follow_url = urljoin(url, link.get('href'))
        try:
            screennames += crawl(follow_url, n - 1)
        except:
            print("Error crawling url " + follow_url)

    return list(set(screennames))


def get_user_ids(key="", secret="", token="", token_secret="", screen_names=[]):
    auth = tweepy.OAuthHandler(key, secret)
    auth.set_access_token(token, token_secret)
    api = tweepy.API(auth)

    ids = []
    for name in set(screen_names):
        try:
            user = api.get_user(name)
            print("Identifying user " + name +  " as id " + str(user.id))
            ids.append(str(user.id))
        except:
            print("Error while identifying user " + name)
    return ids


def stream(key="", secret="", token="", token_secret="", follow=[]):
    auth = tweepy.OAuthHandler(key, secret)
    auth.set_access_token(token, token_secret)
    api = tweepy.API(auth)

    stream = tweepy.Stream(auth=api.auth, listener=StreamListener())
    stream.filter(follow=follow, async=True)
    return stream


def direct_message(to, message, key="", secret="", token="", token_secret="", follow=[]):
    auth = tweepy.OAuthHandler(key, secret)
    auth.set_access_token(token, token_secret)
    api = tweepy.API(auth)

    api.send_direct_message(to, text=message)

def update_status(msg, key="", secret="", token="", token_secret="", follow=[]):
    auth = tweepy.OAuthHandler(key, secret)
    auth.set_access_token(token, token_secret)
    api = tweepy.API(auth)

    api.update_status(msg)