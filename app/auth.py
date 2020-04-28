import requests
from collections import namedtuple
from datetime import datetime, timedelta
from dateutil import parser
from app import settings
import pytz


class Auth:
    # String formatted version of timestamp returned by twitch
    twitch_time_fmt = '%a, %d %b %Y %H:%M:%S %Z'

    def __init__(self):
        # Initialize class attributes
        self.client_id = settings.TWITCH_CLIENT_ID
        self._client_secret = settings.TWITCH_CLIENT_SECRET
        self._auth_token = None
        self._bear_token = None
        self.fetched_at = None
        self.expires_at = None
        self.__create_token()

    @property
    def bear_token(self):
        # Check if exists and has value other than None, [], '', 0, or False
        if hasattr(self, '_bear_token') and self._bear_token:
            return self._bear_token
        return self.__create_token().bear_token

    @property
    def auth_token(self):
        # Check if exists and has value other than None, [], '', 0, or False
        if hasattr(self, '_auth_token') and self._auth_token:
            return self._auth_token
        return self.__create_token().auth_token

    def __create_token(self) -> namedtuple:
        Token = namedtuple('Token', ['auth_token', 'bear_token'])
        # Check if exists
        if hasattr(self, '_auth_token') and hasattr(self, '_bear_token'):
            # Check if not None, [], '', 0, or False
            if self._auth_token and self._bear_token:
                return Token(self._auth_token, self._bear_token)

        oauth_url = 'https://id.twitch.tv/oauth2/token'
        auth_params = {
            'client_id':      self.client_id,
            'client_secret':  self._client_secret,
            'grant_type':     'client_credentials'
            }
        with requests.post(oauth_url, data=auth_params) as req:
            self._auth_token = req.json()
            self._bear_token = {
                'Authorization':  'Bearer ' + self._auth_token['access_token'],
                'Client_ID':      self.client_id
                }
        # Capturing & String-Formatting Token Lifetime Information
            self.fetched_at = parser.parse(req.headers['date']).strftime(self.twitch_time_fmt)
            expires_at = parser.parse(self.fetched_at) + timedelta(seconds=self._auth_token['expires_in'])
            # Maintain a 3 day buffer between End-of-Life according to Twitch vs End-of-Life known to this app
            expires_at -= timedelta(days=3)
            self.expires_at = expires_at.strftime(self.twitch_time_fmt)

        return Token(self._auth_token, self._bear_token)


    def is_expired(self) -> bool:
        # Check if doesn't exist and value is not None, [], '', 0, or False
        if not hasattr(self, 'self.expires_at') and not self.expires_at:
            expired = True
        else:
            expired = datetime.utcnow().astimezone(tz=pytz.utc) > parser.parse(self.expires_at)

        return expired


    def validate(self):
        """ This function validates an instance of this object with Twitch and fetches a new token if not valid """
        valid = False
        # If token has not exceeded lifetime, validate with Twitch
        if self.is_expired():
            oauth_url = 'https://id.twitch.tv/oauth2/validate'
            auth_header = {'Authorization': 'OAuth {}'.format(self._auth_token['access_token'])}
            with requests.get(oauth_url, headers=auth_header) as req:
                # The OAuth token is valid if json response from Twitch contains 'client_id'
                valid = 'client_id' in req.json()

        if not valid:
            self.__create_token()
