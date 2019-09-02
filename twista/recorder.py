import datetime
import time
import gzip
import json
import atexit
import tweepy
import traceback
from termcolor import colored
from twista.dm import TweetObject

class Recorder(tweepy.StreamListener):

    entities = {}
    N = 25000

    # Constructor 
    def __init__(self, n):
        super().__init__()
        self.N = n

    def record(self, ia):
        if ia.type() not in self.entities:
            self.entities[ia.type()] = {}
        self.entities[ia.type()][ia.id()] = ia.as_dict()

    def write(self):
        t = datetime.datetime.utcnow().strftime("%Y-%m-%dT%H-%M")
        with gzip.open("recording-%s.json.gz" % t, 'wt') as file:
            file.write(self.as_json())
        self.entities = {}

    def length(self):
        return sum([len(d.values()) for _, d in self.entities.items()])

    def as_json(self):
        entries = []
        for _, d in self.entities.items():
            entries.extend(d.values())
        return json.dumps(entries, indent=2)

    def on_status(self, status):
        tweet = TweetObject(status._json)
        print(tweet.status().text())

        self.record(tweet.status())
        self.record(tweet.user())
        
        if tweet.is_retweet():
            self.record(tweet.retweet())
            self.record(tweet.retweet().user())
            
            if tweet.retweet().is_quote():
                if tweet.retweet().quote():
                    self.record(tweet.retweet().quote())
                    self.record(tweet.retweet().quote().user())
                
        if tweet.is_quote():
            if tweet.quote():
                self.record(tweet.quote())
                self.record(tweet.quote().user())

        if self.length() >= self.N:
            self.write()
        
    def on_error(self, status_code):
        print("Error")
        print(status_code)
        return False


def recording(config, chunksize, languages, tracks):

    recorder = Recorder(chunksize)
    auth = tweepy.OAuthHandler(config['consumer_key'], config['consumer_secret'])
    auth.set_access_token(config['access_token'], config['access_token_secret'])
    api = tweepy.API(auth)
    stream = tweepy.Stream(auth = api.auth, listener=recorder)

    def shutdown():
        print(colored("Stop recording", "green"))
        recorder.write()
        stream.disconnect()

    atexit.register(shutdown)

    while True:
        try:                        
            stream = tweepy.Stream(auth = api.auth, listener=recorder)
            stream.filter(track=tracks, languages=languages)
        except Exception as ex:
            print(colored("Stream broken. Retrying ...", "red"))
            print(colored(ex, "red"))
            print(colored(traceback.format_exc(), "red"))
            time.sleep(10)