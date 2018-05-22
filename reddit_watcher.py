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
    # create an empty set of the deals we will push so that we do not
    # push multiples of overlapping search hits
    deals_to_push = set()
    for search in RedditWatchedSearch.select(): # iterate through all searches
        curr_time = datetime.now()
        result_posts = search.result(print_search_url=False, print_json_result=True)

        for post in result_posts:
            if post.posted_utc < search.last_run_utc:
                break

            deals_to_push.add(RedditDeal(search, post))

        # remember to only update if the pushables were actually sent
        search.last_run_utc = curr_time
        search.save()

    pb.push_iterable(deals_to_push, print_pushes=True)
    db.close()

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

# TODO: Add generalized RedditGetRequest class
class RedditGetRequest:
    def __init__(self, url):
        self._url = url

    @property
    def items(self):
        headers = {
                'User-Agent': self.user_agent
            }

        # TODO: figure out how to include params
        r = requests.get(self.url + '.json', headers = headers)
        # TODO: come up with a less primitive way of determining if the json
        #     result is a post or search
        json_data = r.json() # contains a list of dicts, with each dict containing a result post's data
        listing = self._first_listing(json_data)
        item_list = listing['data']['children'] # contains a list of dicts, with each dict containing a result post's data

        result_posts = []
        for item_data in item_list:
            result_posts.append(RedditPost.decode(item_data))

        return result_posts

    @property
    def url(self):
        return self._url

    @property
    def user_agent(self):
        return USER_AGENT_BEG + USER_AGENT_END

    @staticmethod
    def _first_listing(json_data):
        if isinstance(json_data, list):
            return json_data[0]
        return json_data # otherwise this IS a listing

class RedditSearch:
    _reddit_search_url = 'https://reddit.com/search'
    _reddit_json_search = _reddit_search_url + '.json'

    _def_search_limit = None
    _sort = None

    def __init__(self, query):
        self.query = query

    def result(self, limit = None, print_search_url=False, print_json_result=False):
        headers = {
                'User-Agent': self.user_agent
            }
        payload = self.params(limit = limit)
        # print(self.query)

        r = requests.get(self._reddit_json_search, headers = headers, params = self.query_string(payload))
        json_data = r.json()['data']['children'] # contains a list of dicts, with each dict containing a result post's data
        # if print_search_url: print(r.url) # print json search url
        if print_search_url: print(self.reddit_url) # print human-readable search url
        if print_json_result: print(json.dumps(json_data, indent=2))

        result_posts = []
        for item_data in json_data:
            result_posts.append(RedditPost.decode(item_data))

        return result_posts

    # returns None if there is no result
    def first_result(self):
        result = self.result(limit = 1)
        if len(result) == 0:
            return None
        return result[0]

    @property
    def reddit_url(self):
        return _reddit_search_url + self.query_string(self.params())

    @property
    def user_agent(self):
        return USER_AGENT_BEG + USER_AGENT_END

    @property
    def def_search_limit(self):
        return self._def_search_limit

    @property
    def sort(self):
        return self._sort

    # if sort is redefined in a subclass, it changes the sorting method
    def params(self, limit = None):
        if limit is None: limit = self.def_search_limit
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

    # override the superclass limit and sort, used in RedditSearch.params()
    _def_search_limit = 10
    _sort = 'new'

    class Meta:
        table_name = 'searches'

    # redefine the user agent such that each search has a different one
    @property
    def user_agent(self):
        return USER_AGENT_BEG + self.user_agent_base + '_' + USER_AGENT_END

    def __str__(self):
        return '{self.uuid!s} {self.user_agent_base}'.format(self=self)

class Pushable:
    @property
    def push_title(self):
        raise NotImplementedError

    @property
    def push_body(self):
        raise NotImplementedError

    @property
    def push_url(self):
        raise NotImplementedError

    def _str_data(self):
        return {
            'title': self.push_title,
            'body': self.push_body,
            'url': self.push_url
        }

    def __str__(self):
        return json.dumps(self._str_data(), indent=2)

    def __eq__(self, other):
        if isinstance(other, Pushable):
            return self.push_title == other.push_title and self.push_body == other.push_body and self.url == other.push_url
        return False

    def __hash__(self):
        return 1

class RedditPost(Pushable):
    def __init__(self, title, posted_utc, url):
        self.title      = title
        self.posted_utc = posted_utc # should be datetime object
        self.url        = url

    @staticmethod
    def decode(item_data):
        post_data  = item_data['data']
        title      = post_data['title']
        url        = post_data['url']
        posted_utc = post_data['created_utc']

        # convert the posted_utc integer to a datetime object
        posted_utc = datetime.utcfromtimestamp(int(posted_utc))

        return RedditPost(title, posted_utc, url)

    @property
    def push_title(self):
        return self.title

    @property
    def push_body(self):
        return None

    @property
    def push_url(self):
        return self.url

    def _str_data(self):
        return {
            'title': self.title,
            'url': self.url,
            'post time (utc)': self.posted_utc.strftime("%Y-%m-%d %H:%M:%S")
        }

    def __eq__(self, other):
        if isinstance(other, RedditPost):
            return self.title == other.title and self.url == other.url and self.posted_utc == other.posted_utc
        return False

    def __hash__(self):
        return 1

class RedditDeal(RedditPost):
    def __init__(self, search, post):
        self.search = search
        super().__init__(post.title, post.posted_utc, post.url)

    @property
    def push_title(self):
        return 'New ' + self.search.title.lower() + ' deal: ' + self.title

    def _str_data(self):
        str_data = super()._str_data()
        str_data['result of searches'] = self.search.user_agent_base
        return str_data

class PushbulletAccount:
    user_agent = USER_AGENT_BEG + USER_AGENT_END
    pb_create_push_url = 'https://api.pushbullet.com/v2/pushes'

    def __init__(self, access_token):
        self.access_token = access_token

    def push_link(self, p):
        payload = {
                'type': 'link',
                'title': p.push_title,
                'body': p.push_body,
                'url': p.push_url
            }

        r = requests.post(self.pb_create_push_url, headers = self._post_headers(), json = payload)
        # print(r.json)

    def push_iterable(self, p_list, print_pushes=False):
        if print_pushes: print('Printed the following pushables:')

        for p in p_list:
            # self.push_link(p)
            if print_pushes: print(p)

    def _post_headers(self):
        return {
                'Access-Token': self.access_token,
                'User-Agent': self.user_agent
            }

if __name__ == "__main__":
    main()
