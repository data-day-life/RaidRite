import asyncio
from time import perf_counter

from app.twitch_rec.twitch_client_v2 import TwitchClient
from app.twitch_rec.follower_network import FollowNet



streambots = {'nightbot', 'streamelements'}
follower_bots = {}


class Recommender:

    def __init__(self, streamer_name, sample_sz=300, n_consumers=100):
        self.tc = TwitchClient()
        self.followings_count = None
        self.sample_sz = sample_sz
        self.streamer_name = streamer_name
        self.streamer_id = None
        self.followers = None
        self.total_followers = None
        self.n_consumers = n_consumers



    async def set_streamer(self):
        if self.streamer_id:
            return
        try:
            self.streamer_id = await self.tc.get_uid(self.streamer_name)
        except IndexError:
            print(f'Streamer named "{self.streamer_name}" not found.')
            raise AttributeError('Streamer uid not set.')


    async def gen_suggestions(self, min_mutual=2, n_best=10):
        try:
            await self.set_streamer()
        except AttributeError as err:
            print(f'{err}\nUnable to generate suggestions.  Invalid streamer_id name/id provided.')
            return

        results = {}

        # Get follower network
        folnet = FollowNet(streamer_id=self.streamer_id, tc=self.tc, sample_sz=self.sample_sz, n_cons=self.n_consumers)
        self.followings_count = await folnet.run_queue()

        # Trim followings_count by some lower bound of minimum followings
        trimmed_candidates = {uid: count for uid, count in folnet.followings_counter.items() if count >= min_mutual}

        # Determine which of the trimmed_candidates are currently live
        live_candidates = await self.tc.get_streams(channels=list(trimmed_candidates.keys()))
        live_ids = {streamer.get('user_id', None) for streamer in live_candidates}
        trimmed_candidates = {uid: count for uid, count in trimmed_candidates.items() if uid in live_ids}
        results = trimmed_candidates

        # Get total followers of trimmed, live candidates


        # Compute similarity scores using union and intersection


        # Rank list of live/trimmed candidates by similiarity scores, retain only n_best live/trimmed candidates
        # ranked_candidates = sorted(...)[:n_best]

        # Get profile img url (avatar)


        return results



async def main():

    from app.twitch_rec.colors import Col
    some_name = 'emilybarkiss'
    sample_sz = 300
    n_consumers = 100
    # n_consumers = 2
    print(f'{Col.bold}{Col.yellow}\t<<<<< {some_name}  |  n={sample_sz} >>>>>{Col.end}')
    t = perf_counter()
    rec = Recommender(some_name, sample_sz=sample_sz, n_consumers=n_consumers)
    live_streams = await rec.gen_suggestions()


    print(f'{Col.cyan}⏲ Total Time: {round(perf_counter() - t, 3)} sec {Col.end}')
    print(f'\t{Col.magenta}N consumers: {n_consumers}\n')

    print(f'{Col.green}Suggestions (sz={len(rec.followings_count)}){Col.end}')
    print(rec.followings_count)


    print(f'{Col.green}Live Stream Suggestions (sz={len(live_streams)}){Col.end}')
    print(live_streams)

    print(rec.streamer_id)

    await rec.tc.close()


if __name__ == "__main__":
    asyncio.run(main())
