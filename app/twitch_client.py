import logging
from app import settings
import requests
from app.auth import Auth
from abc import ABC

module_logger = logging.getLogger(__name__+'.py')
auth_args = {'client_id': settings.TWITCH_CLIENT_ID, 'client_secret': settings.TWITCH_CLIENT_SECRET}
auth_token = Auth(**auth_args)


def validate_name(given_name: str) -> dict:
    """
    This function validates a given_name using Twitch's API and returns a dictionary.  No authorization token is
    required for this request (only a valid client_id, read from `settings.py`)
    
    :param str given_name: a streamer's name to be validated
    :return: a dictionary containing key-value pairs as: 'profile_img_url', 'display_name', 'login_name', 'twitch_uid',
    'broadcaster_type', and 'valid' (boolean value)
    :rtype: dict
    """
    if given_name is None:
        err_msg = "'given_name' supplied to validate_name() was 'None' type."
        module_logger.info("err_msg")
        raise ValueError(err_msg)

    if given_name == "":
        err_msg = "'given_name' supplied to validate_name() was empty: ('{}')".format(str(given_name))
        module_logger.info(err_msg)
        raise ValueError(err_msg)

    # Twitch API request parameters
    base_url = 'https://api.twitch.tv/helix/users'
    query_params = {'login': given_name.lower()}
    client_id = {'Client-ID': settings.TWITCH_CLIENT_ID}

    module_logger.info("Twitch API - 'validate_name()' for: " + '"{}"'.format(str(given_name)))
    # Request user information from Twitch API
    with requests.get(base_url, params=query_params, headers=client_id) as req:
        req.encoding = 'utf-8'
        resp = req.json()['data']
        # Supplied name was found if len(resp['data'])  > 0
        if len(resp) == 0:
            err_msg = "Twitch API - 'validate_name()': Supplied name not found on Twitch: " + str(given_name)
            module_logger.info(err_msg)
            raise ValueError(err_msg)
        else:
            resp = resp[0]

        result = {
            'broadcaster_type': resp['broadcaster_type'],
            'profile_img_url':  resp['profile_image_url'],
            'display_name':     resp['display_name'],
            'name':             resp['login'],
            'twitch_uid':       resp['id'],
        }

    success_log_msg = "Twitch API - 'validate_name()' found user: "
    success_log_msg += '"{}" (twitch_uid: {})'.format(result['display_name'], result['twitch_uid'])
    module_logger.info(success_log_msg)

    return result


def get_total_follows_count(twitch_uid: str, to_from: str) -> str:
    """
    This function gets a follow count from twitch (either followers or followings)

    :param str twitch_uid: A twitch user id.  No validation is performed; assumed valid.
    :param str to_from:  When 'to_id", returns followers collection; when 'from_id' returns "followings" collection
    :return: A count of followers as a String
    :rtype: str
    """

    base_url = 'https://api.twitch.tv/helix/users/follows'
    query_params = {to_from: twitch_uid, 'first': 1}
    client_id = {'Client-ID': settings.TWITCH_CLIENT_ID}
    with requests.get(base_url, params=query_params, headers=client_id) as req:
        resp = req.json()['total']

    return resp


def get_all_follows(given_uid: str, to_or_from_id: str, skip_validation: bool = False) -> dict:
    """
    This function gets followers/followings for a given uid.  This works for collecting followers *to* a streamer
    as well as followings *from* general Twitch users.

    :param str given_uid: The uid whose followings will be collected. No validation performed; assumed valid.
    :param str to_or_from_id: Either 'to_id' (for followers *to* a streamer) or 'from_id' (for followers *from*
    a regular user); typically self.to_from may be supplied
    :param bool skip_validation: Skips validating the authentication token when True; useful when called many times
    :return: A dictionary containing 'total_followers' with 'n' keys for each 100 followings
    :rtype: dict
    """
    # Added to avoid excessive token validation when unnecessary (e.g. when running this command a lot)
    if not skip_validation:
        auth_token.validate()
    bear_token = auth_token.__bear_token

    # Twitch API request parameters
    base_url = 'https://api.twitch.tv/helix/users/follows'
    q_params = {to_or_from_id: given_uid, 'first': 100}

    module_logger.info('Twitch API - Collecting followers list for uid: {}'.format(str(given_uid)))
    # Create a new Session object for repeated requests to Twitch API
    with requests.Session() as sess:
        resp = sess.get(base_url, params=q_params, headers=bear_token).json()
        try:
            # Update pagination cursor for next 100
            q_params['after'] = resp['pagination']['cursor']
        except KeyError:
            # A nonfatal KeyError is thrown for the pagination cursor when user has zero followers
            pass
        # Get total from json response, irrespective of Streamer/non-Streamer self.total_followers
        total_follows = resp['total']
        # Get first 100 follows
        result = resp['data']
        # Collect all remaining follows, a list of 100 or less
        for next_100 in range(100, total_follows, 100):
            resp = sess.get(base_url, params=q_params, headers=bear_token).json()
            # Add next_100 key to results dict (like '100', '200', etc.)
            result.extend(resp['data'])
            # Update pagination cursor for next 100
            q_params['after'] = resp['pagination']['cursor']

    return result


class TwitchAccount(ABC):
    """ Super Class for Twitch Accounts

    This class connects to the Twitch API to collect data for streamers and users.  Its primary purpose is to collect
    a list of *followers* for a Streamer or a list of *followings* for non-streamers (TwitchUser).  Results from this
    class can be used with the DB to lookup a user, add/update a user in the DB, and verify that DB records coincide
    with Twitch records (e.g., total_followers, or follow_list)
    """
    def __init__(self):
        self.display_name = None
        self.name = None
        self.twitch_uid = None
        self.is_streamer = False
        self.twitch_follow_list = None
        self.to_from = None

    def validate_attributes(self):
        """
        This function simply checks whether a 'twitch_uid' and a 'to_from' attribute have been defined.
        :return:
        """
        if self.twitch_uid is None:
            raise ValueError("Twitch user id must be supplied before collecting follow list but twitch_uid was 'None'.")
        if self.to_from is None:
            raise ValueError("A follower direction (to_id or from_id) must be provided but was 'None'")

    def get_all_follows(self):
        self.validate_attributes()
        if self.twitch_follow_list is None:
            module_logger.info('No followers list set.  Collecting a list of ALL followers from Twitch...')
            self.twitch_follow_list = get_all_follows(self.twitch_uid, self.to_from)

        return self.twitch_follow_list

    def get_total_follows_count(self):
        self.validate_attributes()
        return get_total_follows_count(self.twitch_uid, self.to_from)


class TwitchStreamer(TwitchAccount):
    def __init__(self, streamer_name: str):
        try:
            valid_streamer = validate_name(str(streamer_name))
        except ValueError as e:
            module_logger.info('Cannot create TwitchStreamer() object: Supplied name not valid ', e)
            return

        # Super class call
        super().__init__()

        self.profile_img_url = None
        self.broadcaster_type = None
        self.is_streamer = True
        # Set to_from field for get_all_follows: get dict of people this user *is followed by*
        self.to_from = 'to_id'

        # Set attributes using validate_name() results (a dict)
        for k, v in valid_streamer.items():
            setattr(self, k, v)

        # Fetch a count of total followers for this streamer
        self.total_followers = super().get_total_follows_count()

    def as_dict(self) -> dict:
        result = {'twitch_uid':         self.twitch_uid,
                  'name':               self.name,
                  'display_name':       self.display_name,
                  'streamer':           self.is_streamer,
                  'profile_img_url':    self.profile_img_url,
                  'broadcaster_type':   self.broadcaster_type,
                  'total_followers':    self.total_followers
                  }
        return result


class TwitchUser(TwitchAccount):
    def __init__(self, **kwargs):
        # Super class call
        super().__init__()
        # Set attributes using supplied kwargs (a twitch_uid is expected)
        for key, val in kwargs.items():
            if hasattr(self, key):
                setattr(self, key, val)

        # Set to_from field for get_all_follows: gets list of people this user *is following*
        self.to_from = 'from_id'

        # Fetch a count of total followers for this streamer
        self.total_followings = super().get_total_follows_count()
