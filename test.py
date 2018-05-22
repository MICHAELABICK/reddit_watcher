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
        self.test_posts = [
                {
                    'type': 'manual',
                    'title': 'Test Title',
                    'url': 'www.thisisatest.com',
                    'posted_utc': 123456
                },
                {
                    'type': 'get_req',
                    'title': 'NVMe recommendations',
                    'url': 'https://www.reddit.com/r/homelab/comments/79z05m/nvme_recommendations/',
                    'posted_utc': 1509485184
                }
            ]

        for tp in self.test_posts:
            if tp['type'] == 'manual':
                post_data = {
                        'title':       tp['title'],
                        'url':         tp['url'],
                        'created_utc': str(tp['posted_utc'])
                    }
                item_data = {'data': post_data}
                post_obj = RedditPost.decode(item_data)
            else:
                post_obj = RedditGetRequest(tp['url']).items[0]

            tp['post'] = post_obj

    def test_pushable_props(self):
        for p in self.test_posts:
            with self.subTest('Post creation type: ' + p['type']):
                post_obj = p['post']
                self.assertEqual(post_obj.push_title, p['title'])
                self.assertEqual(post_obj.push_body, None)
                self.assertEqual(post_obj.push_url, p['url'])

    def test_str(self):
        for p in self.test_posts:
            with self.subTest('Post creation type: ' + p['type']):
                post_obj = p['post']
                self.assertIsInstance(str(post_obj), str)


if __name__ == '__main__':
    unittest.main()
