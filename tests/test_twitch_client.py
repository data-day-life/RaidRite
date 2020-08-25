import unittest
from app.twitch_client import TwitchStreamer

# Removed from setUp to speed up tests -- could break at some point since streamer is set
streamer = TwitchStreamer('stroopc')

class TestStreamer(unittest.TestCase):
    def setUp(self):
        pass

    def tearDown(self):
        pass

    def test_Streamer_has_name(self):
        self.assertEqual(streamer.name, 'stroopc')
        self.assertTrue(streamer.name is not None)

    def test_Streamer_has_uid(self):
        self.assertTrue(streamer.twitch_uid is not None)
        self.assertFalse(streamer.twitch_uid == '')
        self.assertEqual(streamer.twitch_uid, '106071345')

    def test_Streamer_has_tot_followers(self):
        # As of last check, stroopC has 465 followers; floor is set to 450 for future-proofing
        self.assertTrue(streamer.live_uid_total_followers > 450)

    def test_Streamer_has_foll_list(self):
        # Test whether get_follows produces a non-empty list
        foll_result = streamer.get_all_follows()
        self.assertTrue(len(foll_result) > 0)

    def test_Streamer_foll_list_size_matches_total_followers(self):
        foll_result = streamer.get_all_follows()
        self.assertTrue (len(foll_result) > 0)
        self.assertEqual(len(foll_result), streamer.live_uid_total_followers)
        self.assertEqual(len(foll_result), streamer.get_total_follows_count())

    def test_Streamer_zero_follower_list_is_okay(self):
        zero_streamer = TwitchStreamer('prod3x')
        foll_result = zero_streamer.get_all_follows()
        # This twitch user has 0 total followers
        self.assertFalse(len(foll_result) > 0)
        self.assertEqual(len(foll_result), 0)
        self.assertEqual(len(foll_result), zero_streamer.live_uid_total_followers)
        self.assertEqual(zero_streamer.live_uid_total_followers, 0)
        self.assertEqual(zero_streamer.get_total_follows_count(), 0)
        self.assertEqual(int(zero_streamer.get_total_follows_count()), len(foll_result))

    def test_Streamer_small_follower_list_is_okay(self):
        very_small_streamer = TwitchStreamer('moJohat')
        foll_result = very_small_streamer.get_all_follows()
        # This twitch user has 9 total followers
        self.assertTrue(len(foll_result) > 0)
        self.assertEqual(len(foll_result), very_small_streamer.get_total_follows_count())
        self.assertEqual(len(foll_result), very_small_streamer.live_uid_total_followers)
        self.assertEqual(very_small_streamer.live_uid_total_followers, very_small_streamer.get_total_follows_count())
        self.assertEqual(int(very_small_streamer.get_total_follows_count()), len(foll_result))

if __name__ == '__main__':
    unittest.main()
