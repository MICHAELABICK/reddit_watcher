import unittest
from reddit_watcher import *
import urllib

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

            self.assertIsInstance(result, list)
            self.assertEqual(len(result), limit)
            self.assertIsInstance(result[27], RedditPost)

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
                self.assertIn('python:com.michaelbick.reddit_watcher:v', s.user_agent())

    def test_query_string(self):
        for s in self.searches:
            with self.subTest('Query: "{s.query}"'.format(s=s)):
                params = s.params()
                qs = RedditSearch.query_string(params)
                decoded_params = urllib.parse.parse_qs(qs)
                decoded_query = decoded_params['q'][0]

                self.assertEqual(s.query, decoded_query)

if __name__ == '__main__':
    unittest.main()
