import requests
from datetime import datetime, timedelta
from dateutil import parser
import pytz


class Auth:
    # String formatted version of timestamp returned by twitch
    twitch_time_fmt = '%a, %d %b %Y %H:%M:%S %Z'

    def __init__(self, **kwargs):
        if 'client_id' not in kwargs and 'client_secret' not in kwargs:
            raise ValueError("'client_id' and 'client_secret' must be provided as dictionary.")

        # Initialize class attributes
        self.client_id = kwargs.pop('client_id')
        self.client_secret = kwargs.pop('client_secret')
        self.auth_tok = None
        self.bear_tok = None
        self.fetched_at = None
        self.expires_at = None

        # Set attributes using supplied kwargs (a twitch_uid is expected)
        for key, val in kwargs.items():
            if hasattr(self, key):
                setattr(self, key, val)

        # Request a new auth token if not supplied as an argument or if supplied auth_token was not valid
        if ('auth_tok' not in kwargs) or (not self.validate()):
            self.get_token()

    def get_token(self):
        oauth_url = 'https://id.twitch.tv/oauth2/token'
        auth_params = {
            'client_id':      self.client_id,
            'client_secret':  self.client_secret,
            'grant_type':     'client_credentials'
            }
        with requests.post(oauth_url, data=auth_params) as req:
            self.auth_tok = req.json()
            self.bear_tok = {
                'Authorization':  'Bearer ' + self.auth_tok['access_token'],
                'Client_ID':      self.client_id
                }
        # Capturing & String-Formatting Token Lifetime Information
            self.fetched_at = parser.parse(req.headers['date']).strftime(self.twitch_time_fmt)
            expires_at = parser.parse(self.fetched_at) + timedelta(seconds=self.auth_tok['expires_in'])
            # Maintain a 3 day buffer between End-of-Life according to Twitch vs End-of-Life known to this app
            expires_at -= timedelta(days=3)
            self.expires_at = expires_at.strftime(self.twitch_time_fmt)

        # This syntax merges two dictionaries into a single dictionary
        return {**self.auth_tok, **self.bear_tok}

    def not_expired(self) -> bool:
        return datetime.utcnow().astimezone(tz=pytz.utc) < parser.parse(self.expires_at)

    def validate(self):
        """ This function validates an instance of this object with Twitch and fetches a new token if not valid """
        valid = False
        # If token has not exceeded lifetime, validate with Twitch
        if self.not_expired():
            oauth_url = 'https://id.twitch.tv/oauth2/validate'
            auth_header = {'Authorization': 'OAuth {}'.format(self.auth_tok['access_token'])}
            with requests.get(oauth_url, headers=auth_header) as req:
                # The OAuth token is valid if json response from Twitch contains 'client_id'
                valid = 'client_id' in req.json()

        if not valid:
            self.get_token()
