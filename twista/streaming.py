import tweepy
import uuid
import bs4
import requests
import re
import json
from urllib.parse import urljoin
from selenium import webdriver
import time
import random
import traceback

from twista.analysis import Tweet
from twista.analysis import TwistaList

BROWSER = webdriver.PhantomJS()
JSON_INDENT = 3
CHUNK_SIZE = 1000


class StreamListener(tweepy.StreamListener):

    def __init__(self):
        self.tweets = []
        self.memory_mentions = []
        self.memory_hashtags = []
        self.memory_retweeters = []
        self.memory_retweeteds = []
        self.memory_quoters = []
        self.memory_quoteds = []

        self.chunk_file = self.new_chunk()

    def new_chunk(self):
        chunk = "chunk-" + str(uuid.uuid4()) + ".json"
        print("New chunk " + chunk)
        return chunk

    '''
    Returns observed user mentions.
    '''
    def mentions(self):
        return TwistaList(self.memory_mentions)

    '''
    Returns observed hashtags.
    '''
    def hashtags(self):
        return TwistaList(self.memory_hashtags)

    '''
    Returns ids of observed retweeters.
    '''
    def retweeters(self):
        return TwistaList(self.memory_retweeters)

    '''
    Returns ids of observed retweeted accounts.
    '''
    def retweeteds(self):
        return TwistaList(self.memory_retweeteds)

    '''
    Returns ids of observed quoters.
    '''
    def quoters(self):
        return TwistaList(self.memory_quoters)

    '''
    Returns ids of observed quoted accounts.
    '''
    def quoteds(self):
        return self.memory_quoteds

    def remember(self, mentions=1000, hashtags=1000, retweeters=1000, retweeteds=1000, quoters=1000, quoteds=1000):
        if len(self.memory_mentions) > mentions:
            self.memory_mentions = self.memory_mentions[-mentions:]

        if len(self.memory_hashtags) > hashtags:
            self.memory_hashtags = self.memory_hashtags[-hashtags:]

        if len(self.memory_retweeters) > retweeters:
            self.memory_retweeters = self.memory_retweeters[-retweeters:]

        if len(self.memory_retweeteds) > retweeteds:
            self.memory_retweeteds = self.memory_retweeteds[-retweeteds:]

        if len(self.memory_quoters) > quoters:
            self.memory_quoters = self.memory_quoters[-quoters:]

        if len(self.memory_quoteds) > quoteds:
            self.memory_quoteds = self.memory_quoteds[-quoteds]

    def on_data(self, raw_data):
        try:
            data = json.loads(raw_data)

            tweet = Tweet(data)

            if not tweet.is_deleted() and not tweet.is_withheld():
                print(tweet.user().screen_name() + ": " + tweet.text())

                if tweet.retweeted_status():
                    self.memory_retweeters.append(tweet.user().id())
                    self.memory_retweeteds.append(tweet.retweeted_status().user().id())

                if tweet.quoted_status():
                    self.memory_quoters.append(tweet.user().id())
                    self.memory_quoteds.append(tweet.quoted_status().user().id())

                self.memory_mentions += tweet.user_mentions()
                self.memory_hashtags += tweet.hashtags()

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


def load(url, scrolldown=10, js_enabled=False):
    print(url + ": " + str(js_enabled))
    if js_enabled:
        BROWSER.get(url)
        time.sleep(1)
        for i in range(0, scrolldown):
            BROWSER.execute_script("window.scrollTo(0, document.body.scrollHeight);")
            time.sleep(1)

        return BROWSER.page_source
    else:
        res = requests.get(url)
        return res.text

def crawl_for_screennames(url, js_enabled=False):
    print("Crawling " + url)
    screennames = []
    #res = requests.get(url)
    html = load(url, js_enabled=js_enabled)
    #soup = bs4.BeautifulSoup(res.text, 'html5lib')
    soup = bs4.BeautifulSoup(html, 'html5lib')
    for link in soup.select('a[href^=http://twitter.com/], a[href^=https://twitter.com/], a[href^=http://www.twitter.com/], a[href^=https://www.twitter.com/]'):
        href = link.get('href')
        href = href.replace('https://', '')
        href = href.replace('http://', '')
        href = href.replace('www.twitter.com/', '')
        href = href.replace('twitter.com/', '')

        screenname = re.findall(r"[A-Za-z0-9_]+", href)[0]
        if not screenname in ['flickr', 'signup', 'privacy', 'share', 'home']:
            print("Found @" + screenname)
            screennames.append(screenname)

    return screennames

visited = []

def crawl(url, n=0, js_enabled=False):
    if url in visited:
        print("Skipping " + url + ": Already visited.")
        return []

    screennames = crawl_for_screennames(url, js_enabled=js_enabled)
    visited.append(url)
    if n == 0:
        return list(set(screennames))

    #res = requests.get(url)
    html = load(url, js_enabled=js_enabled)
    #soup = bs4.BeautifulSoup(res.text, 'html5lib')
    soup = bs4.BeautifulSoup(html, 'html5lib')
    for link in soup.select('a[href]'):
        print(link.get('href'))
        follow_url = urljoin(url, link.get('href'))
        try:
            screennames += crawl(follow_url, n - 1, js_enabled=js_enabled)
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


def stream(key="", secret="", token="", token_secret="", follow=None, track=None, language='de'):
    auth = tweepy.OAuthHandler(key, secret)
    auth.set_access_token(token, token_secret)
    api = tweepy.API(auth)

    stream = tweepy.Stream(auth=api.auth, listener=StreamListener())

    if follow:
        print("Following: " + str(follow))
        stream.filter(follow=follow, languages=[language], async=True)
        return stream

    if track:
        print("Tracking: " + str(track))
        stream.filter(track=track, languages=[language], async=True)
        return stream

    stream.sample(languages=[language], async=True)
    return stream