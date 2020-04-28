from app.auth import Auth
from app import settings
import unittest


class TestAuth(unittest.TestCase):
    def setUp(self):
        self.test_auth = Auth()

    def test_auth_has_cid(self):
        self.assertEqual(self.test_auth.client_id, settings.TWITCH_CLIENT_ID)

    def test_auth_has_secr(self):
        self.assertEqual(self.test_auth._client_secret, settings.TWITCH_CLIENT_SECRET)

    def test_auth_has_auth_tok(self):
        self.assertTrue(hasattr(self.test_auth, '_auth_token'))
        self.assertFalse(self.test_auth._auth_token == "")
        self.assertTrue('access_token' in self.test_auth._auth_token)
        self.assertTrue(len(self.test_auth._auth_token['access_token']) > 0)
        self.assertFalse(self.test_auth._auth_token['access_token'] == "")

    def test_auth_has_bear_tok(self):
        self.assertTrue(hasattr(self.test_auth, '_bear_token'))
        self.assertFalse(self.test_auth._bear_token == "")
        # Check Authorization field
        self.assertTrue('Authorization' in self.test_auth._bear_token)
        self.assertTrue(len(self.test_auth._bear_token['Authorization']) > 0)
        self.assertFalse(self.test_auth._bear_token['Authorization'] == "")
        # Check Client_ID field
        self.assertTrue('Client_ID' in self.test_auth._bear_token)
        self.assertTrue(len(self.test_auth._bear_token['Client_ID']) > 0)
        self.assertFalse(self.test_auth._bear_token['Client_ID'] == "")


if __name__ == '__main__':
    unittest.main()
