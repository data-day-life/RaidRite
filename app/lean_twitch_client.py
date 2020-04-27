import logging
import requests
from app.auth import Auth
from collections import namedtuple, Counter
from time import perf_counter
from dateutil.parser import parse as dt_parse
from datetime import datetime as dt
from pytz import utc

module_logger = logging.getLogger(__name__+'.py')


def get_name_info(given_name: str, bear_token=None) -> dict:
    if bear_token is None:
        bear_token = Auth().bear_token
    # Twitch API request parameters
    base_url = 'https://api.twitch.tv/helix/users'
    query_params = {'login': given_name.lower()}

    module_logger.info("Twitch API - 'validate_name()' for: " + '"{}"'.format(str(given_name)))
    # Request user information from Twitch API
    with requests.get(base_url, params=query_params, headers=bear_token) as req:
        req.encoding = 'utf-8'
        resp = req.json()['data'][0]

        result = {
            'broadcaster_type': resp['broadcaster_type'],
            'profile_img_url': resp['profile_image_url'],
            'display_name': resp['display_name'],
            'name': resp['login'],
            'twitch_uid': resp['id'],
        }

    return result


class TwitchClient:
    """ This class connects to the Twitch API to collect data for streamers and users. """

    Streamer = namedtuple('Streamer', ['uid', 'to_from'], defaults=['to_id'])
    Follower = namedtuple('Follower', ['uid', 'to_from'], defaults=['from_id'])
    MIN_FOLLOWINGS = 2

    def __init__(self, streamer_uid, n_followers=100, n_followings=100):
        self.auth = Auth()
        self.bear_token = self.auth.bear_token
        self.sess = requests.Session()
        self.streamer = self.Streamer(streamer_uid, 'to_id')
        self.followers_list = None
        self.followings_count = None
        self.n_followings = n_followings
        self.n_followers = n_followers
        if self.n_followers is None:
            self.n_followers = self.get_total_follows_count(streamer_uid)


    def get_n_follows(self, given_uid: str, to_or_from_id: str, n_follows=None) -> list:
        """
        This function collects followers/followings data for a given user id.  This function can be used to collect
        followers *to* a streamer as well as followings *from* regular Twitch users.

        :param str given_uid: A valid user id whose follows will be collected. No validation performed; assumed valid.
        :param str to_or_from_id: Either 'to_id' (for followers *to* a streamer) or 'from_id' (for followers *from*
        a regular user)
        :param int n_follows: Collects data for up to n_follows if provided; collects all follows otherwise
        :return: A list of dictionaries containing all follow information collected from Twitch; parsing left to caller.
        """
        req_batch_sz = 100
        base_url = 'https://api.twitch.tv/helix/users/follows'
        q_params = {to_or_from_id: given_uid, 'first': req_batch_sz}
        resp = self.sess.get(base_url, params=q_params, headers=self.bear_token).json()
        try:  # Update pagination cursor for next request batch
            q_params['after'] = resp['pagination']['cursor']
        except KeyError:
            pass  # A nonfatal KeyError is thrown for the pagination cursor when user has zero followers

        result = resp['data']
        total_follows = resp['total']

        # Modify number of followers to be collected by given parameter if necessary
        if n_follows is not None:
            if n_follows < total_follows:
                total_follows = n_follows
        module_logger.info(f'Collecting {total_follows} follows for "{given_uid}"')

        for next_batch in range(req_batch_sz, total_follows, req_batch_sz):
            resp = self.sess.get(base_url, params=q_params, headers=self.bear_token).json()
            # Add next_batch to results
            result.extend(resp['data'])
            # Update pagination cursor for next batch
            try:
                q_params['after'] = resp['pagination']['cursor']
            except KeyError:
                break

        return result


    def get_streamer_followers(self) -> list:
        """
        Creates a list of follower id's with size self.n_followers for self.streamer.  If n_followers was not provided
        during initialization of the class object then all followers of a streamer are collected.

        :return: A list of follower ids as strings: ['follower_uid1', 'follower_uid2', ...]
        """
        if self.followers_list is None:
            followers = self.get_n_follows(self.streamer.uid, self.streamer.to_from, self.n_followers)
            follower_ids = [self.Follower(follower['from_id'], 'from_id') for follower in followers]
            self.followers_list = follower_ids

        return self.followers_list


    def get_followers_followings(self) -> dict:
        """
        This function aggregates counts of all user id's that a streamer's followers are following.  That is, if a
        streamer has two followers and both followers are following some other streamer then the aggregated count is
        collected as {'other_streamer_id: 2}.  This result provides the follower overlap (intersection) between
        self.streamer and other streamers.

        :return: A dictionary of {'other_streamer_uid1': count, 'other_streamer_uid2': count, ...}
        """

        start_time = perf_counter()
        # Get streamer's followers if list does not exist
        if self.followers_list is None:
            self.get_streamer_followers()

        tot_collected = 0
        if self.followings_count is None:
            self.followings_count = Counter()
            for follower in self.followers_list:
                followings = self.get_n_follows(follower.uid, follower.to_from, self.n_followings)
                self.followings_count.update([following['to_id'] for following in followings])
                tot_collected += len(followings)

        runtime = round(perf_counter() - start_time, 2)
        module_logger.info(f'Collected {self.n_followings} followings '
                           f'for {self.n_followers} followers -- {tot_collected} total @ {runtime} sec')

        return self.followings_count


    def get_total_follows_count(self, twitch_uid: str) -> str:
        """
        This function fetches the count of all followers as reported by Twitch for the supplied twitch_uid.

        :param str twitch_uid: A valid twitch user id.  No validation is performed; assumed valid.
        :return: A count of total followers as a String.
        """
        base_url = 'https://api.twitch.tv/helix/users/follows'
        query_params = {'to_id': twitch_uid, 'first': 1}

        return self.sess.get(base_url, params=query_params, headers=self.bear_token).json()['total']


    def get_similar_streams(self, result_size=10) -> dict:
        """
        This function handles the "magic" behind retrieving similar streams recommendations.  A list of candidates is
        created by eliminating candidates below a minimum threshold of follower overlap then further reduced by
        determining which candidates are currently live.  A similarity score is computed for the list of live candidates
        before sorting in descending order of similarity.  Profile images are also fetched for the final 'result_size"
        list of best candidates.

        :param result_size: The desired amount of similar streams.
        :return: A dictionary formatted as {'1': {best candidate details}, '2': {second best candidate details}, ...}
        which provides the final json response for the frontend.
        """
        if self.followings_count is None:
            self.get_followers_followings()

        trimmed_candidates = {uid: count for uid, count in self.followings_count.items()
                              if count >= self.MIN_FOLLOWINGS}
        # Remove *this* streamer from list of candidates
        trimmed_candidates.pop(self.streamer.uid, None)
        live_candidates = self.get_live_streams(list(trimmed_candidates.keys()))
        trimmed_candidates = {uid: count for uid, count in trimmed_candidates.items() if uid in live_candidates}

        streamer_followers_count = self.n_followers
        for candidate_id in live_candidates:
            intersection_total_followers = trimmed_candidates[candidate_id]
            union_total_followers = streamer_followers_count + self.get_total_follows_count(candidate_id)
            trimmed_candidates[candidate_id] = intersection_total_followers / union_total_followers

        if result_size > len(trimmed_candidates):
            result_size = len(trimmed_candidates)
        # Rank Candidates, retaining only 'result_size' final candidates
        ranked_candidates = sorted(trimmed_candidates.items(),
                                   key=lambda similarity: similarity[1], reverse=True)[:result_size]
        ranked_prof_img_urls = self.get_prof_img_url([candidate[0] for candidate in ranked_candidates])

        final_candidates = {}
        for rank, candidate in enumerate(ranked_candidates[:result_size]):
            uid, sim_score = candidate
            live_candidates[uid]['sim_score'] = sim_score
            live_candidates[uid]['profile_image_url'] = ranked_prof_img_urls[uid]
            final_candidates[rank+1] = live_candidates[uid]

        return final_candidates


    def get_prof_img_url(self, streamer_uid_list: list) -> dict:
        """
        This function collects profile image urls for a given list of (candidate) user ids (strings).

        :param streamer_uid_list: A list of candidate uids for collecting respective profile image urls.
        :return: A dictionary as {'candidate1_uid': 'profile url', 'candidate2_uid': ...}
        """
        max_batch_sz = 100
        req_batch_sz = len(streamer_uid_list) if len(streamer_uid_list) < max_batch_sz else max_batch_sz
        base_url = 'https://api.twitch.tv/helix/users'
        q_params = {'id': streamer_uid_list[:req_batch_sz], 'first': req_batch_sz}

        # Fetch live streams for first req_batch_sz candidate streams
        resp = self.sess.get(base_url, params=q_params, headers=self.bear_token).json()
        user_data = resp['data']

        if len(streamer_uid_list) > req_batch_sz:
            # Collect all remaining live streams
            for next_batch in range(req_batch_sz, len(streamer_uid_list), req_batch_sz):
                q_params = {'id': streamer_uid_list[next_batch:next_batch+req_batch_sz], 'first': req_batch_sz}
                resp = self.sess.get(base_url, params=q_params, headers=self.bear_token).json()
                user_data.extend(resp['data'])

        return {user['id']: user['profile_image_url'] for user in user_data}


    def get_live_streams(self, streamer_uid_list: list) -> dict:
        """
        This function takes a streamer_uid_list and returns a dictionary of user id's that are currently broadcasting on
        Twitch.  It is primarily useful for filtering out a large list of raid candidates that are not live.  This
        function also provides details for live streams (such as number of viewers and a recent thumbnail of a live
        broadcast).

        :param streamer_uid_list: A list of candidate streams as user ids (strings).
        :return: A nested dictionary of live streams information as {'stream_uid1: {details...}, 'stream_uid': ...}
        """
        req_batch_sz = 100  # CANNOT be larger than 100
        base_url = 'https://api.twitch.tv/helix/streams'
        q_params = {'user_id': streamer_uid_list[:req_batch_sz], 'first': req_batch_sz}

        # Fetch live streams for first req_batch_sz candidate streams
        resp = self.sess.get(base_url, params=q_params, headers=self.bear_token).json()
        live_list = resp['data']

        # Collect all remaining live streams
        if len(streamer_uid_list) > req_batch_sz:
            for next_batch in range(req_batch_sz, len(streamer_uid_list), req_batch_sz):
                q_params = {'user_id': streamer_uid_list[next_batch:next_batch+req_batch_sz], 'first': req_batch_sz}
                resp = self.sess.get(base_url, params=q_params, headers=self.bear_token).json()
                live_list.extend(resp['data'])

        def duration(twitch_time):
            diff = (dt.now(utc) - dt_parse(twitch_time)).total_seconds()
            return f'{int(diff//3600)}hr {int((diff%3600)//60)}min'

        live_list = {
            usr['user_id']: {
                     'name': usr['user_name'],
                     'stream_title': usr['title'],
                     'stream_url': 'https://www.twitch.tv/' + usr['user_name'],
                     'thumbnail_url': usr['thumbnail_url'],
                     'viewer_count': usr['viewer_count'],
                     'stream_duration': duration(usr['started_at']),
                     'lang': usr['language']
                    }
            for usr in live_list}

        # print(live_list)
        # print(f'Count of live streams {len(live_list)} out of {len(streamer_uid_list)} candidates')
        return live_list
