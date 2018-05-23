import unittest
import pytest
from reddit_watcher import *
import urllib
from datetime import datetime

# helper function to test lists
def assert_list_is_expected(self, test_list, limit, list_type):
    self.assertIsInstance(test_list, list)
    self.assertTrue(len(test_list) <= limit)
    for post in test_list:
        self.assertIsInstance(post, list_type)

# helper functions to test dicts
def assert_value_equal(self, key, dict1, dict2):
    self.assertEqual(dict1[key], dict2[key])

def assert_value_not_equal(self, key, dict1, dict2):
    self.assertNotEqual(dict1[key], dict2[key])

class BaseTestCases():
    class BaseRedditPostTestCase(unittest.TestCase):
        def setUp(self):
            self.base_post    = self.base_post_format.copy()
            self.get_req_post = self.get_req_post_format.copy()

            self.copy1     = self.base_post.copy()
            self.copy2     = self.base_post.copy()
            self.dif_title = self.base_post.copy()
            self.dif_url   = self.base_post.copy()
            self.dif_time  = self.base_post.copy()

            self.copy2['type'] = 'constructor'
            self.dif_title['title'] = 'Different Title'
            self.dif_url['url'] = 'www.difurl.com'
            self.dif_time['posted_utc'] = 111111

class RedditSearchTestCase(unittest.TestCase):
    def setUp(self):
        self.no_res_search = RedditSearch('it is impossible for there to be results 02415927&32#@1?5')
        self.many_res_search = RedditSearch('reddit')
        self.searches = [
                self.no_res_search,
                self.many_res_search
            ]

        queries = [
                'this is a search query',
                'this AND that',
                'days OR nights',
                '(complicated AND search) OR (queries but) NOT simple',
                '"also check" AND ("that quotes" OR "work too")',
                'how about gib%$3@!^)(-_eriSh'
            ]
        for q in queries:
            self.searches.append(RedditSearch(q))

    # remember that this WILL error if not connected to the internet
    def test_result(self):
        with self.subTest("A search with no results"):
            s = self.no_res_search
            self.assertEqual(s.result(), [])

        with self.subTest("A search with many results"):
            s = self.many_res_search
            limit = 42
            result = s.result(limit = limit)
            assert_list_is_expected(self, result, limit, RedditPost)

    # remember that this WILL error if not connected to the internet
    def test_first_result(self):
        with self.subTest("A search with no results"):
            s = self.no_res_search
            self.assertIsNone(s.first_result())

        with self.subTest("A search with many results"):
            s = self.many_res_search
            self.assertIsInstance(s.first_result(), RedditPost)

    def test_user_agent(self):
        for s in self.searches:
            with self.subTest('Query: "{s.query}"'.format(s=s)):
                self.assertIn('python:com.michaelbick.reddit_watcher:v', s.user_agent)

    # TODO: Test params

    def test_query_string(self):
        for s in self.searches:
            with self.subTest('Query: "{s.query}"'.format(s=s)):
                params = s.params()
                qs = RedditSearch.query_string(params)
                decoded_params = urllib.parse.parse_qs(qs)
                decoded_query = decoded_params['q'][0]

                self.assertEqual(s.query, decoded_query)

class RedditWatchedSearchTestCase(unittest.TestCase):
    def setUp(self):
        self.searches = RedditWatchedSearch.select()

    # remember that this WILL error if not connected to the internet
    def test_result(self):
        for s in self.searches:
            with self.subTest('Default limit search: {s.title}'.format(s=s)):
                def_limit = s.def_search_limit
                result = s.result()
                assert_list_is_expected(self, result, def_limit, RedditPost)

            with self.subTest('Search with limit: {s.title}'.format(s=s)):
                limit = 25
                result = s.result(limit = limit)
                assert_list_is_expected(self, result, limit, RedditPost)

    def test_user_agent(self):
        for s in self.searches:
            with self.subTest('Search Title: {s.title}'.format(s=s)):
                user_agent = s.user_agent
                self.assertIn('python:com.michaelbick.', user_agent)
                self.assertIn(s.user_agent_base, user_agent)
                self.assertIn('reddit_watcher:v', user_agent)

    # TODO: Test params

    def test_str(self):
        for s in self.searches:
            with self.subTest('Search Title: {s.title}'.format(s=s)):
                string = str(s)
                self.assertIn(str(s.uuid), string)
                self.assertIn(s.user_agent_base, string)

class Surround():
    class TestRedditPost:
        @property
        def post(self):
            raise NotImplementedError()

        @property
        def expected_title(self):
            raise NotImplementedError()

        @property
        def expected_url(self):
            raise NotImplementedError()

        @property
        def expected_time(self):
            raise NotImplementedError()

        def test_props(self):
            assert self.post.title == self.expected_title
            assert self.post.url == self.expected_url
            assert self.post.posted_utc == self.expected_time

        def test_pushable_props(self):
            assert self.post.push_title == self.expected_title
            assert self.post.push_body == None
            assert self.post.push_url == self.expected_url

        def test_str(self):
            assert isinstance(str(self.post), str)

class TestRedditPostFromConstructor(Surround.TestRedditPost):
    title = 'Test Title'
    url = 'www.thisisatest.com'
    posted_utc_int = 123456

    @property
    def posted_utc(self): return datetime.utcfromtimestamp(self.posted_utc_int)

    @property
    def post(self): return RedditPost(self.title, self.url, self.posted_utc)

    @property
    def expected_title(self): return self.title

    @property
    def expected_url(self): return self.url

    @property
    def expected_time(self): return self.posted_utc

# class TestRedditPostFromConstructor2(TestRedditPostFromConstructor):
#     title = 'Different Title'

# class TestRedditPostFromConstructor3(TestRedditPostFromConstructor):
#     url = 'www.difurl.com'

# class TestRedditPostFromConstructor4(TestRedditPostFromConstructor):
#     posted_utc_int = 111111

class TestRedditPostFromDecode(TestRedditPostFromConstructor):
    @property
    def post(self):
        post_data = {
                'title':       self.title,
                'url':         self.url,
                'created_utc': str(self.posted_utc_int)
            }
        item_data = {'data': post_data}
        return RedditPost.decode(item_data)

class TestRedditPostFromGETRequest(Surround.TestRedditPost):
    url  = 'https://www.reddit.com/r/homelab/comments/79z05m/nvme_recommendations/'
    post = RedditGetRequest(url).items[0]

    expected_title = 'NVMe recommendations'
    expected_url   = url
    expected_time  = datetime.utcfromtimestamp(1509485184)

# class TestRedditPostEquality(unittest.TestCase):
#     def test_eq(self):
        # print(str(TestRedditPostFromConstructor.post.title))
        # self.assertEqual(TestRedditPostFromConstructor.post, \
        #         TestRedditPostFromDecode.post)
        # self.assertNotEqual(TestRedditPost.post, \
        #         TestRedditPostFromConstructor2.post)
        # self.assertNotEqual(TestRedditPost.post, \
        #         TestRedditPostFromConstructor3.post)
        # self.assertNotEqual(TestRedditPost.post, \
        #         TestRedditPostFromConstructor4.post)

class RedditPostTestCase(BaseTestCases.BaseRedditPostTestCase):
    base_post_format = {
            'type': 'decode',
            'title': 'Test Title',
            'url': 'www.thisisatest.com',
            'posted_utc': 123456
        }
    get_req_post_format = {
        'type': 'get_req',
        'title': 'NVMe recommendations',
        'url': 'https://www.reddit.com/r/homelab/comments/79z05m/nvme_recommendations/',
        'posted_utc': 1509485184
    }

    def setUp(self):
        super().setUp()

        self.test_posts = [
                self.base_post,
                self.copy1,
                self.copy2,
                self.dif_title,
                self.dif_url,
                self.dif_time,
                self.get_req_post
            ]

        for tp in self.test_posts:
            if tp['type'] == 'decode':
                post_data = {
                        'title':       tp['title'],
                        'url':         tp['url'],
                        'created_utc': str(tp['posted_utc'])
                    }
                item_data = {'data': post_data}
                post_obj = RedditPost.decode(item_data)
            elif tp['type'] == 'constructor':
                post_obj = RedditPost(tp['title'], tp['url'], datetime.utcfromtimestamp(tp['posted_utc']))
            else:
                post_obj = RedditGetRequest(tp['url']).items[0]

            tp['post'] = post_obj

    def test_eq(self):
        assert_value_equal(self, 'post', self.base_post, self.copy1)
        assert_value_equal(self, 'post', self.base_post, self.copy2)
        assert_value_not_equal(self, 'post', self.base_post, self.dif_title)
        assert_value_not_equal(self, 'post', self.base_post, self.dif_url)
        assert_value_not_equal(self, 'post', self.base_post, self.dif_time)

# TODO: Write tests for RedditDeal


if __name__ == '__main__':
    unittest.main()
