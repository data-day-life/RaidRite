import asyncio
from app.twitch_client_v2 import TwitchClient
from collections import Counter
from app.bot_detection import BotDetector
from time import perf_counter


streambots = {'nightbot', 'streamelements'}
follower_bots = {}


class Recommender:

    def __init__(self, streamer_name, sample_sz=300):
        self.loop = asyncio.get_event_loop()
        self.tc = TwitchClient(loop=self.loop)
        self.followings_counter = Counter()
        self.sample_sz = sample_sz
        self.streamer_name = streamer_name
        self.streamer_id = None
        self.followers = None
        self.total_followers = None
        self.has_clean_foll_list = False


    async def set_streamer(self):
        if self.streamer_id:
            return
        try:
            self.streamer_id = await self.tc.get_uid(self.streamer_name)
        except IndexError:
            print(f'Streamer named "{self.streamer_name}" not found.')
            raise AttributeError('Streamer uid not set.')


    async def gen_suggestions(self):
        try:
            await self.set_streamer()
        except AttributeError as err:
            print(f'{err}\nUnable to generate suggestions.  Invalid streamer name/id provided.')
            return

        results = {}
        # TODO: ? Check if stream is live, if true then Prioritize Active viewers -- ignore streambots

        # Get streamer's followers
        clean_uids = await self.produce_follower_samples()
        results = clean_uids


        # Get Followings of followers and add uids of followings to followings_counter


        # Add uids that followers are following to followings_counter


        # Trim followings_count by some lower bound of minimum followings
        # trimmed_candidates = {uid: count for uid, count in self.followings_counter.items()
        #                       if count >= self.MIN_FOLLOWINGS}


        # Remove *this* streamer from list of trimmed_candidates
        # trimmed_candidates.pop(streamer_id.uid, None)

        # Determine which of the trimmed_candidates are currently live
        # live_candidates = self.get_live_streams(list(trimmed_candidates.keys()))
        # trimmed_candidates = {uid: count for uid, count in trimmed_candidates.items() if uid in live_candidates}

        # Get total followers of streamer


        # Get total followers of trimmed, live candidates


        # Compute similarity scores using union and intersection


        # Rank list of live/trimmed candidates by similiarity scores, retain only n_best live/trimmed candidates
        # ranked_candidates = sorted(...)[:n_best]

        # Get profile img url (avatar)


        return results


    # async def parse_follower_ids(self, follower_reply_data: list) -> list:
    #     return [follower['from_id'] for follower in follower_reply_data]


    async def produce_follower_samples(self):
        """
        Utilizes twitch client to collect a list of follower_ids for valid streamer_id while removing follower bots.

        Returns:
            A list of sanitized follower uids; length is not necessarily equal to sample_sz.
        """
        if not self.streamer_id:
            await self.set_streamer()

        follower_reply = await self.tc.get_full_n_followers(self.streamer_id, self.sample_sz)
        next_cursor = follower_reply.get('cursor', None)
        if not self.total_followers:
            self.total_followers = follower_reply.get('total', 0)

        bd = BotDetector()
        all_sanitized_uids = await bd.santize_foll_list(follower_reply.get('data', None))

        while next_cursor and (len(all_sanitized_uids) < self.sample_sz):
            # print(f'Total sanitized uids: {len(all_sanitized_uids)}')
            params = [('after', next_cursor)]
            next_foll_reply = await self.tc.get_full_n_followers(self.streamer_id, self.sample_sz, params=params)
            next_sanitized_uids = await bd.santize_foll_list(next_foll_reply.get('data', None))
            all_sanitized_uids.extend(next_sanitized_uids)
            next_cursor = next_foll_reply.get('cursor', None)

        # print(f'> Removed {bd.total_removed} potential follower bots total.')
        # print(f'> Total sanitized uids: {len(all_sanitized_uids)}')

        return all_sanitized_uids



async def main():
    t = perf_counter()
    some_name = 'stroopc'
    rec = Recommender(some_name)

    print(await rec.gen_suggestions())
    print(f'Total Time: {round(perf_counter() - t, 3)} sec')
    # print(await rec.produce_follower_samples())

    await rec.tc.close()


if __name__ == "__main__":
    asyncio.run(main())
