import asyncio
from app.twitch_client_v2 import TwitchClient
from app.streamer import Streamer
from app.follower_network import FollowNet
from time import perf_counter
from app.colors import Col


class LiveStreamInfo:

    def __init__(self):
        self.live_streams = list()
        self.uid_totals = dict()
        self.num_live_stream_calls_to_twitch = 0
        self.fetched_batches = list()


    def __str__(self, result='\n'):
        result += f'{Col.orange}<<<<< Live Stream Info {Col.end}\n'
        result += f'{Col.white}  * Calls to Twitch: {self.num_live_stream_calls_to_twitch}{Col.end}\n'
        result += f'{Col.orange} > Total Fetched Batches (sz={len(self.fetched_batches)}):{Col.end}\n'
        result += f'     {self.fetched_batches}\n'
        result += f'{Col.orange} > Live Streams (sz={len(self.live_streams)}):{Col.end}\n'
        result += f'     {self.live_streams}\n'
        result += f'{Col.orange} > Tot. Followers, Live Streams (sz={len(self.uid_totals)}):{Col.end}\n'
        result += f'     {self.uid_totals}\n'

        return result


    @staticmethod
    def filter_language(live_streams, lang='en'):
        return [ls for ls in live_streams if ls.get('language', None) == lang]


    @staticmethod
    def dictify(live_stream_list):
        return {stream.get('user_id'): stream for stream in live_stream_list}


    async def produce_live_streams(self, tc: TwitchClient, q_in: asyncio.Queue, q_out: asyncio.Queue = None):
        while True:
            candidate_batch = await q_in.get()
            self.fetched_batches.extend(candidate_batch)
            # TODO: May not need this any more ?
            # Flatten if first item is list
            # if isinstance(candidate_batch[0], list):
            #     found_live_streams = []
            #     for batch in candidate_batch:
            #         found_live_streams.extend(await self.fetch_live_streams(tc, batch, filter_lang=True, lang='en'))
            #
            # else:
            #     found_live_streams = await self.fetch_live_streams(tc, candidate_batch, filter_lang=True, lang='en')
            found_live_streams = await self.fetch_live_streams(tc, candidate_batch, filter_lang=True, lang='en')
            self.live_streams.extend(found_live_streams)

            if q_out:
                [q_out.put_nowait(stream.get('user_id', None)) for stream in found_live_streams]
            q_in.task_done()



    async def consume_live_streams(self, tc: TwitchClient, q_in: asyncio.Queue, q_out: asyncio.Queue = None):
        while True:
            live_streamer_uid = await q_in.get()
            total_followers = await tc.get_total_followers(int(live_streamer_uid))
            # self.live_streams.get(live_streamer_uid).update({'total': total_followers})
            self.uid_totals[live_streamer_uid] = total_followers

            if q_out:
                pass
            q_in.task_done()


    async def fetch_live_streams(self, tc: TwitchClient, candidates, filter_lang=True, lang='en'):
        live_candidates = await tc.get_streams(channels=candidates)
        if filter_lang:
            live_candidates = self.filter_language(live_candidates, lang=lang)
        self.num_live_stream_calls_to_twitch += 1

        return live_candidates


    async def run(self, tc: TwitchClient, streamer: Streamer, folnet: FollowNet, n_consumers=50):

        # async with TwitchClient() as tc2:
        q_foll_ids = asyncio.Queue()
        q_followings = asyncio.Queue()
        q_live_uids = asyncio.Queue()

        t_prod = asyncio.create_task(streamer.produce_follower_ids(tc, q_out=q_foll_ids))
        t_followings = [asyncio.create_task(
            folnet.produce_followed_ids(tc, q_in=q_foll_ids, q_out=q_followings)) for _ in range(n_consumers)]
        t_livestreams = asyncio.create_task(self.produce_live_streams(tc, q_in=q_followings, q_out=q_live_uids))
        t_total = [asyncio.create_task(
            self.consume_live_streams(tc, q_in=q_live_uids)) for _ in range(n_consumers//2)]

        await asyncio.gather(t_prod)
        print(streamer)

        await q_foll_ids.join()
        [q_followings.put_nowait(batch) for batch in folnet.new_candidate_batches(remainder=True)]
        print(folnet)

        #
        await q_followings.join()
        print(self)
        await q_live_uids.join()
        print(self)


        [t.cancel() for t in t_followings]
        t_livestreams.cancel()
        [t.cancel() for t in t_total]


        await tc.close()


async def main():
    t = perf_counter()
    some_name = 'emilybarkiss'
    sample_sz = 300
    n_consumers = 100

    tc = TwitchClient()
    streamer = Streamer(name=some_name, sample_sz=sample_sz)
    folnet = FollowNet(streamer_id=streamer.uid)
    ls = LiveStreamInfo()
    await ls.run(tc, streamer, folnet, n_consumers)

    print(streamer)
    print(folnet)
    print(ls)

    print(f'{Col.magenta}🟊 N consumers: {n_consumers} {Col.end}')
    print(f'{Col.cyan}⏲ Total Time: {round(perf_counter() - t, 3)} sec {Col.end}')
    from datetime import datetime
    print(f'{Col.red}\t««« {datetime.now().strftime("%I:%M.%S %p")} »»» {Col.end}')


if __name__ == "__main__":
    asyncio.run(main())
