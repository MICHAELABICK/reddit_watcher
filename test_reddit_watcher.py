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

@pytest.fixture(scope="class", params=[
    'base',
    'copy',
    'dif_title',
    'dif_url',
    'dif_time',
    'decode',
    'get_req'
])
def post_test_case(request):
    # print('New post_test_case created: {}'.format(request.param))
    return reddit_post_test_case_factory(request.param)

@pytest.mark.usefixtures("post_test_case")
class TestRedditPostCreation:
    def test_props(self, post_test_case):
        assert post_test_case.post.title == post_test_case.expected_title
        assert post_test_case.post.url == post_test_case.expected_url
        assert post_test_case.post.posted_utc == post_test_case.expected_time

    def test_push_title(self, post_test_case):
        assert post_test_case.post.push_title == post_test_case.expected_title

    def test_push_body(self, post_test_case):
        assert post_test_case.post.push_body == None

    def test_push_url(self, post_test_case):
        assert post_test_case.post.push_url == post_test_case.expected_url

    def test_str(self, post_test_case):
        assert isinstance(str(post_test_case.post), str)

def reddit_post_test_case_factory(case_abbrev):
    class ManualBase:
        title          = 'Test Title'
        url            = 'www.thisisatest.com'
        posted_utc_int = 123456

    class Base(ManualBase, RedditPostFromConstructorTestCase):
        case_abbrev    = 'base'

    class Copy(Base):
        case_abbrev = 'copy'

    class DifTitle(Base):
        case_abbrev = 'dif_title'
        title       = 'Dif Title'

    class DifURL(Base):
        case_abbrev = 'dif_url'
        url         = 'www.difurl.com'

    class DifTime(Base):
        case_abbrev    = 'dif_time'
        posted_utc_int = 111111

    class Decode(ManualBase, RedditPostFromDecodeTestCase):
        case_abbrev = 'decode'

    class GETRequest(RedditPostFromGETRequestTestCase):
        case_abbrev    = 'get_req'
        url            = 'https://www.reddit.com/r/homelab/comments/79z05m/nvme_recommendations/'
        expected_title = 'NVMe recommendations'
        expected_url   = url
        expected_time  = datetime.utcfromtimestamp(1509485184)

    if isinstance(case_abbrev, str):
        # return test case with given case_abbrev
        test_cases = RedditPostTestCase.recursive_subclasses()
        for tc in test_cases:
            # print(tc)
            try:
                if tc.case_abbrev == case_abbrev:
                    return tc()
            except NotImplementedError:
                pass

        print(test_cases)
        raise ValueError
    else:
        raise TypeError

class RedditPostTestCase:
    @property
    def case_abbrev(self): raise NotImplementedError

    @property
    def post(self): raise NotImplementedError

    @property
    def expected_title(self): raise NotImplementedError

    @property
    def expected_url(self): raise NotImplementedError

    @property
    def expected_time(self): raise NotImplementedError

    @classmethod
    def recursive_subclasses(cls):
        cls_subs = cls.__subclasses__()
        subs = set(cls_subs)
        for sub in cls_subs:
            subs = subs.union(sub.recursive_subclasses())
        # print(subs)
        return subs

class RedditPostCreatedManuallyTestCase(RedditPostTestCase):
    @property
    def title(self): raise NotImplementedError

    @property
    def url(self): raise NotImplementedError

    @property
    def posted_utc_int(self): raise NotImplementedError

    @property
    def posted_utc(self): return datetime.utcfromtimestamp(self.posted_utc_int)

    @property
    def expected_title(self): return self.title

    @property
    def expected_url(self): return self.url

    @property
    def expected_time(self): return self.posted_utc

class RedditPostFromConstructorTestCase(RedditPostCreatedManuallyTestCase):
    @property
    def post(self): return RedditPost(self.title, self.url, self.posted_utc)

class RedditPostFromDecodeTestCase(RedditPostCreatedManuallyTestCase):
    @property
    def post(self):
        post_data = {
                'title':       self.title,
                'url':         self.url,
                'created_utc': str(self.posted_utc_int)
            }
        item_data = {'data': post_data}
        return RedditPost.decode(item_data)

class RedditPostFromGETRequestTestCase(RedditPostTestCase):
    @property
    def post(self):
       return RedditGetRequest(self.url).items[0]

# def test_reddit_post_eq(self):
#     print(str(TestRedditPostFromConstructor.post.title))
#     self.assertEqual(TestRedditPostFromConstructor.post, \
#             RedditPostFromDecodeTestCase.post)
#     self.assertNotEqual(TestRedditPost.post, \
#             TestRedditPostFromConstructor2.post)
#     self.assertNotEqual(TestRedditPost.post, \
#             TestRedditPostFromConstructor3.post)
#     self.assertNotEqual(TestRedditPost.post, \
#             TestRedditPostFromConstructor4.post)

# TODO: Write tests for RedditDeal
# class RedditDealTestCase(RedditPostTestCase):
#     @property
#     def expected_searches(self):
#         raise NotImplementedError


if __name__ == '__main__':
    unittest.main()
