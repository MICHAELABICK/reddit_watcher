import secrets
import json
import urllib
import requests
from datetime import datetime
from peewee import *

VERSION = 'v1.0.0'
DATABASE = 'reddit_watcher.db'
USER_AGENT_BEG = 'python:com.michaelbick.'
USER_AGENT_END = 'reddit_watcher:' + VERSION

PB_ACCESS_TOKEN = secrets.pb_access_token

db = SqliteDatabase(DATABASE)

def main():
    db.connect()
    pb = PushbulletAccount(PB_ACCESS_TOKEN)

    # TODO: currently it still pushes multiple because every pushable that
        # is created is actually different
    # create an empty set of the posts we will push so that we do not
    # push multiples of overlapping search hits
    posts_to_push = set()
    for search in RedditWatchedSearch.select(): # iterate through all searches
        curr_time = datetime.now()
        result_posts = search.result(print_search_url=False, print_json_result=False)

        for post in result_posts:
            if post.posted_utc < search.last_run_utc:
                break

            posts_to_push.add(create_pushable(search, post))

        # remember to only update if the pushables were actually sent
        search.update_last_run_utc(curr_time)

    pb.push_iterable(posts_to_push, print_pushes=True)
    db.close()

def create_pushable(search, post):
    title = 'New ' + search.title.lower() + ' deal: ' + post.title
    # print(title)
    return Pushable(title=title, url=post.url)

# helper function to create tables
def create_tables():
    with db:
        db.create_tables([RedditWatchedSearch])

# testing functions
def push_test():
    test = Pushable(title = 'Test Push')
    pb = PushbulletAccount(PB_ACCESS_TOKEN)
    pb.push_link(test)

# model definitions -- the standard "pattern" is to define a base model class
# that specifies which database to use.  then, any subclasses will automatically
# use the correct storage.
class BaseModel(Model):
    class Meta:
        database = db

    # will fail if the subclasses' __str__ method fails
    @classmethod
    def list(cls):
        for record in cls.select(): # iterate through all searches
            print(record)

class RedditSearch:
    reddit_search_url = 'https://reddit.com/search'
    reddit_json_search = reddit_search_url + '.json'
    # TODO: determine if I can pass self.default_search_limit as a default argument

    sort = None

    def __init__(self, query):
        self.query = query

    def result(self, limit = None, print_search_url=False, print_json_result=False):
        headers = {
                'User-Agent': self.user_agent()
            }
        payload = self.params(limit = limit)
        # print(self.query)

        r = requests.get(self.reddit_json_search, headers = headers, params = self.query_string(payload))
        json_data = r.json()['data']['children'] # contains a list of dicts, with each dict containing a result post's data
        # if print_search_url: print(r.url) # print json search url
        if print_search_url: print(self.reddit_url) # print human-readable search url
        if print_json_result: print(json.dumps(json_data, indent=2))

        result_posts = []
        for post_data in json_data:
            result_posts.append(RedditPost.decode(post_data))

        return result_posts

    # returns None if there is no result
    def first_result(self):
        result = self.result(limit = 1)
        if len(result) == 0:
            return None
        return result[0]

    def reddit_url(self):
        return reddit_search_url + self.query_string(self.params())

    def user_agent(self):
        return USER_AGENT_BEG + USER_AGENT_END

    # if sort is redefined in a subclass, it changes the sorting method
    def params(self, limit = None):
        return {
                'limit': limit,
                'q': self.query,
                'sort': self.sort,
                'type': 'link'
            }

    @staticmethod
    def query_string(params):
        # custom encode the params to make the query string shorter
        return urllib.parse.urlencode(params, safe='()')

class RedditWatchedSearch(BaseModel, RedditSearch):
    uuid            = UUIDField()
    title           = TextField()
    query           = TextField()
    user_agent_base = TextField()
    last_run_utc    = TimestampField()

    sort = 'new'

    class Meta:
        table_name = 'searches'

    def result(self, limit = 10, print_search_url=False, print_json_result=False):
        return super().result(limit = limit,
                print_search_url = print_search_url,
                print_json_result = print_json_result)

    def update_last_run_utc(self, last_run_utc):
        self.last_run_utc = last_run_utc
        self.save()

    # redefine the user agent such that each search has a different one
    def user_agent(self):
        return USER_AGENT_BEG + self.user_agent_base + '_' + USER_AGENT_END

    def __str__(self):
        return '{self.uuid!s} {self.user_agent_base}'.format(self=self)

class RedditPost:
    def __init__(self, title, posted_utc, url):
        self.title      = title
        self.posted_utc = posted_utc
        self.url        = url

    @staticmethod
    def decode(post_data):
        title      = post_data['data']['title']
        url        = post_data['data']['url']
        posted_utc = post_data['data']['created_utc']

        # convert the posted_utc integer to a datetime object
        posted_utc = datetime.utcfromtimestamp(int(posted_utc))

        return RedditPost(title, posted_utc, url)

    def __eq__(self, other):
        if isinstance(other, Pushable):
            return self.title == other.title and self.url == other.url and self.posted_utc == other.posted_utc
        return False

    def __hash__(self):
        return 1

class Pushable:
    def __init__(self, title = None, body = None, url = None):
        self.title = title
        self.body  = body
        self.url  = url

    def __str__(self):
        return 'title: {self.title}, body: {self.body}, url: {self.url}'.format(self=self)

    def __eq__(self, other):
        if isinstance(other, Pushable):
            return self.title == other.title and self.body == other.body and self.url == other.url
        return False

    def __hash__(self):
        return 1

class PushbulletAccount:
    user_agent = USER_AGENT_BEG + USER_AGENT_END
    pb_create_push_url = 'https://api.pushbullet.com/v2/pushes'

    def __init__(self, access_token):
        self.access_token = access_token

    def push_link(self, p):
        payload = {
                'type': 'link',
                'title': p.title,
                'body': p.body,
                'url': p.url
            }

        r = requests.post(self.pb_create_push_url, headers = self._post_headers(), json = payload)
        # print(r.json)

    def push_iterable(self, p_list, print_pushes=False):
        for p in p_list:
            self.push_link(p)
            if print_pushes: print(p)

    def _post_headers(self):
        return {
                'Access-Token': self.access_token,
                'User-Agent': self.user_agent
            }

if __name__ == "__main__":
    main()
