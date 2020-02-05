import json
import datetime
import twista
from dateutil import parser

class TweetObject:
    
    def __init__(self, json):
        self.json = json
        self.json['created_at'] = parser.parse(self.json['created_at']).isoformat()
        self.json['recorded_at'] = datetime.datetime.now(tz=datetime.timezone.utc).isoformat()
        
    def id(self):
        return self.json['id_str']
    
    def type(self):
        if (self.is_user()):
            return "user"
        if (self.is_status()):
            return "status" 
        if (self.is_retweet()):
            return "retweet" 
        if (self.is_quote()):
            return "quote" 
        if (self.is_reply()):
            return "reply"
        return "unknown"
    
    def created_at(self):
        return self.json['created_at']
    
    def recorded_at(self):
        return self.json['recorded_at']
    
    def user(self):
        return User(self.json['user'])
        
    def text(self):
        return self.json['text']
        
    def is_user(self):
        return "screen_name" in self.json

    def is_status(self):
        return not (self.is_quote() or self.is_reply() or self.is_retweet())
    
    def is_quote(self):
        return self.json['is_quote_status'] and "retweeted_status" not in self.json
    
    def is_reply(self):
        return self.json['in_reply_to_status_id_str'] != None
    
    def reply_to_status_id(self):
        return self.json['in_reply_to_status_id_str']
    
    def is_retweet(self):
        return "retweeted_status" in self.json
    
    def quote(self):
        if 'quoted_status' not in self.json:
            return None
        return Status(self.json['quoted_status'])
    
    def retweet(self):
        return Status(self.json['retweeted_status']) if self.is_retweet() else None
    
    def status(self):
        return Status(self.json)
    
    def __str__(self):
        return json.dumps(self.json, indent=4)
    
    
class Entities:
    
    def __init__(self, json):
        self.json = json
        
    def hashtags(self):
        return [e['text'] for e in self.json['hashtags']]

    def urls(self):
        return [e['url'] for e in self.json['urls']]
    
    def mentions(self):
        return [e['screen_name'] for e in self.json['user_mentions']]

    def mentioned_ids(self):
        res = [e['id_str'] for e in self.json['user_mentions']]
        return [r for r in res if r is not None]
    
    def as_dict(self):
        return {
            "hashtags": self.hashtags(),
            "urls": self.urls(),
            "mentions": self.mentions(),
            "mentioned_ids": self.mentioned_ids()         
        }
    
    def __str__(self):
        return json.dumps(self.as_dict(), indent=4)
        

    
class Status(TweetObject):
        
    def text(self):
        if 'extended_tweet' in self.json:
            return self.json['extended_tweet']['full_text']
        return self.json['text']
    
    def entities(self):
        if 'extended_tweet' in self.json:
            return Entities(self.json['extended_tweet']['entities'])
        return Entities(self.json['entities'])
    
    def as_dict(self):

        rts = self.json['retweet_count']
        favs = self.json['favorite_count']

        r = {
            'twista': twista.VERSION,
            "type": self.type(),
            "id": self.id(),
            "user": self.user().id(),
            "created_at": self.created_at(),
            "recorded_at": self.recorded_at(),
            "source": self.json['source'],
            "retweets": rts if rts else 0,
            "favourites": favs if favs else 0,
            "lang": self.json['lang']
        }

        r.update(self.entities().as_dict())

        if not self.is_retweet():
            r['text'] = self.text()

        if self.is_quote():
            if 'quoted_status_id_str' in self.json:
                r['refers_to'] = self.json['quoted_status_id_str']

        if self.is_retweet():
            r['refers_to'] = self.retweet().id()

        if self.is_reply():
            r['refers_to'] = self.reply_to_status_id()
            
        return r
    
    
class User(TweetObject):
                
    def screenname(self):
        return self.json['screen_name']
    
    def name(self):
        return self.json['name']

    def as_dict(self):
        return {
            'twista': twista.VERSION,
            'type': 'user',
            'id': self.id(),
            'name': self.name(), # Since Version 0.3.1b
            'screen_name': self.screenname(),
            'created_at': self.created_at(),
            'recorded_at': self.recorded_at(),
            'location': self.json['location'],
            'description': self.json['description'],
            'url': self.json['url'],
            'verified': self.json['verified'],
            # 'lang': self.json['lang'], deprecated meanwhile
            'followers': self.json['followers_count'],
            'friends': self.json['friends_count'],
            'listed': self.json['listed_count'],
            'favourites': self.json['favourites_count'],
            'statuses': self.json['statuses_count']
        }