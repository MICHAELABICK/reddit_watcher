import unittest
from reddit_watcher import *
import urllib
from datetime import datetime

# helper function to test lists
def assert_list_is_expected(self, test_list, limit, list_type):
    self.assertIsInstance(test_list, list)
    self.assertTrue(len(test_list) <= limit)
    for post in test_list:
        self.assertIsInstance(post, list_type)

class RedditSearchTestCase(unittest.TestCase):
    def setUp(self):
        queries = [
                'this is a search query',
                'this AND that',
                'days OR nights',
                '(complicated AND search) OR (queries but) NOT simple',
                '"also check" AND ("that quotes" OR "work too")',
                'how about gib%$3@!^)(-_eriSh'
            ]
        searches = []
        for q in queries:
            searches.append(RedditSearch(q))

        no_res_search = RedditSearch('it is impossible for there to be results 02415927&32#@1?5')
        many_res_search = RedditSearch('reddit')
        searches.extend([no_res_search, many_res_search])

        self.no_res_search = no_res_search
        self.many_res_search = many_res_search
        self.searches = searches

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

class RedditPostTestCase(unittest.TestCase):
    def setUp(self):
        post1_data = {
                'title': 'Test Title',
                'created_utc': '123456',
                'url': 'www.thisisatest.com'
            }
        item1_data = {'data': post1_data}
        post1 = RedditPost.decode(item1_data)

        post2_data = {
                'title': 'NVMe recommendations',
                'url': 'https://www.reddit.com/r/homelab/comments/79z05m/nvme_recommendations/',
                'posted_utc': 10
            }
        items2 = RedditGetRequest(post2_data['url']).items

        self.post1_data = post1_data
        self.post1 = post1
        self.post2_data = post2_data
        self.post2 = items2[0]
        self.posts = [post1, self.post2]

    def test_pushable_props(self):
        with self.subTest('Manually Created Post'):
            self.assertEqual(self.post1.push_title, self.post1_data['title'])
            self.assertEqual(self.post1.push_body, None)
            self.assertEqual(self.post1.push_url, self.post1_data['url'])

        with self.subTest('Post from URL'):
            self.assertEqual(self.post2.push_title, self.post2_data['title'])
            self.assertEqual(self.post2.push_body, None)
            self.assertEqual(self.post2.push_url, self.post2_data['url'])

    def test_str(self):
        with self.subTest('Manually Created Post'):
            self.assertIsInstance(str(self.post1), str)

        with self.subTest('Post from URL'):
            self.assertIsInstance(str(self.post2), str)


if __name__ == '__main__':
    unittest.main()
