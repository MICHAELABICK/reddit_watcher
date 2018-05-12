import unittest
from reddit_watcher import RedditSearch
import urllib

class RedditSearchTestCase(unittest.TestCase):
    def setUp(self):
        queries = [
                'this is a search query',
                'this AND that',
                'days OR nights',
                '(complicated AND search) OR (queries but) NOT simple'
            ]
        searches = []
        for q in queries:
            searches.append(RedditSearch(q))

        self.searches = searches

    def test_query_string(self):
        for s in self.searches:
            with self.subTest(s=s):
                params = s.params()
                qs = RedditSearch.query_string(params)
                decoded_params = urllib.parse.parse_qs(qs)
                decoded_query = decoded_params['q'][0]

                self.assertEqual(s.query, decoded_query)

if __name__ == '__main__':
    unittest.main()
