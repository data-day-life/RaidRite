import asyncio
from time import perf_counter
from typing import List, Dict
from dateutil.parser import parse as dt_parse
from datetime import datetime as dt
from pytz import utc
from app.twitch_rec.twitch_client import TwitchClient
from app.twitch_rec.streamer import Streamer
from app.twitch_rec.follower_network import FollowNet
from app.twitch_rec.colors import Col


class LiveStreamInfo:
    live_streams:       List[Dict[str, str]] = list()
    uid_totals:         Dict[str, str] = dict()
    fetched_batches:    List[str] = list()
    num_ls_reqs:        int = 0

    def __init__(self) -> None:
        pass


    def __repr__(self):
        return (f'{self.__class__.__name__}('
                f'{self.num_ls_reqs!r}, {self.fetched_batches!r}, {self.live_streams!r}, {self.uid_totals!r})')


    def __str__(self, result=''):
        result += f'{Col.orange}<<<<< Live Stream Info {Col.end}\n'
        result += f'{Col.white}  * Calls to Twitch: {self.num_ls_reqs}{Col.end}\n'
        result += f'{Col.orange} > Total Fetched Batches (sz={len(self.fetched_batches)}):{Col.end}\n'
        result += f'     {self.fetched_batches}\n'
        result += f'{Col.orange} > Live Streams (sz={len(self.live_streams)}):{Col.end}\n'
        result += f'     {self.live_streams}\n'
        result += f'{Col.orange} > Tot. Followers, Live Streams (sz={len(self.uid_totals)}):{Col.end}\n'
        result += f'     {self.uid_totals}\n'

        return result


    async def __call__(self, tc: TwitchClient, q_in_followings: asyncio.Queue, q_out: asyncio.Queue = None, n_cons=50):
        q_live_uids = asyncio.Queue()
        t_livestreams = asyncio.create_task(self.produce_live_streams(tc, q_in=q_in_followings, q_out=q_live_uids))
        t_total = [asyncio.create_task(
            self.consume_live_streams(tc, q_in=q_live_uids)) for _ in range(n_cons)]

        await q_in_followings.join()
        t_livestreams.cancel()

        await q_live_uids.join()
        [t.cancel() for t in t_total]



    @staticmethod
    def filter_language(live_streams, lang='en'):
        return [ls for ls in live_streams if ls.get('language', None) == lang]


    @staticmethod
    def dictify(live_stream_list):
        return {stream.get('user_id'): stream for stream in live_stream_list}


    @staticmethod
    def parse_duration(twitch_time):
        diff = (dt.now(utc) - dt_parse(twitch_time)).total_seconds()
        return f'{int(diff // 3600)}hr {int((diff % 3600) // 60)}min'


    def apply_stream_duration(self, livestreams):
        [stream.update({'stream_duration': self.parse_duration(stream.get('started_at'))})
            for stream in livestreams]


    async def produce_live_streams(self, tc: TwitchClient, q_in: asyncio.Queue, q_out: asyncio.Queue = None):
        while True:
            candidate_batch = await q_in.get()
            self.fetched_batches.extend(candidate_batch)
            found_live_streams = await self.fetch_live_streams(tc, candidate_batch, filter_lang=True, lang='en')
            self.apply_stream_duration(found_live_streams)
            self.live_streams.extend(found_live_streams)

            if q_out:
                [q_out.put_nowait(stream.get('user_id', None)) for stream in found_live_streams]
            q_in.task_done()


    async def consume_live_streams(self, tc: TwitchClient, q_in: asyncio.Queue, q_out: asyncio.Queue = None):
        while True:
            live_streamer_uid = await q_in.get()
            total_followers = await tc.get_total_followers(int(live_streamer_uid))
            # TODO: Keep uids+totals separate from live stream uid info or update ls uid info with total?
            # self.live_streams.get(live_streamer_uid).update({'total': total_followers})
            self.uid_totals[live_streamer_uid] = total_followers

            if q_out:
                pass
            q_in.task_done()


    async def fetch_live_streams(self, tc: TwitchClient, candidates, filter_lang=True, lang='en'):
        live_candidates = await tc.get_streams(channels=candidates)
        if filter_lang:
            live_candidates = self.filter_language(live_candidates, lang=lang)
        self.num_ls_reqs += 1

        return live_candidates



async def run_v2(tc: TwitchClient, streamer: Streamer, folnet: FollowNet, ls: LiveStreamInfo, n_consumers=50):
    print('\n\n********** Run V2 ********** ')
    q_foll_ids = asyncio.Queue()
    q_followings = asyncio.Queue()
    q_live_uids = asyncio.Queue()

    t_prod = asyncio.create_task(streamer.produce_follower_ids(tc, q_out=q_foll_ids))
    t_followings = [asyncio.create_task(
        folnet.produce_followed_ids(tc, q_in=q_foll_ids, q_out=q_followings)) for _ in range(n_consumers)]
    # t_livestreams = asyncio.create_task(self.produce_live_streams(tc, q_in=q_followings, q_out=q_live_uids))
    # t_total = [asyncio.create_task(
    #     self.consume_live_streams(tc, q_in=q_live_uids)) for _ in range(n_consumers//2)]

    # Streamer: follower ids
    await asyncio.gather(t_prod)
    print(streamer)

    # Folnet: follower's followings
    await q_foll_ids.join()

    # task creation must follow q_foll_ids.join() b/c the join produces q_followings
    t_ls = asyncio.create_task(ls(tc, q_in_followings=q_followings, n_cons=n_consumers//2))
    [q_followings.put_nowait(batch) for batch in folnet.new_candidate_batches(remainder=True)]
    [t.cancel() for t in t_followings]
    print(folnet)

    # LiveStreams
    await q_followings.join()
    # print(self)

    await q_live_uids.join()

    # task creation must follow q_foll_ids.join() b/c the join produces q_followings
    # t_ls = asyncio.create_task(self.__call__(tc, q_in_followings=q_followings))
    await asyncio.gather(t_ls)
    t_ls.cancel()



async def run_v1(tc: TwitchClient, streamer: Streamer, folnet: FollowNet, ls: LiveStreamInfo, n_consumers=50):
    print('\n\n********** Run V1 ********** ')
    q_foll_ids = asyncio.Queue()
    q_followings = asyncio.Queue()
    q_live_uids = asyncio.Queue()

    t_prod = asyncio.create_task(streamer.produce_follower_ids(tc, q_out=q_foll_ids))
    t_followings = [asyncio.create_task(
        folnet.produce_followed_ids(tc, q_in=q_foll_ids, q_out=q_followings)) for _ in range(n_consumers)]
    t_livestreams = asyncio.create_task(ls.produce_live_streams(tc, q_in=q_followings, q_out=q_live_uids))
    t_total = [asyncio.create_task(
        ls.consume_live_streams(tc, q_in=q_live_uids)) for _ in range(n_consumers//2)]

    # Streamer: follower ids
    await asyncio.gather(t_prod)
    # print(streamer)

    # Folnet: follower's followings
    await q_foll_ids.join()
    [q_followings.put_nowait(batch) for batch in folnet.new_candidate_batches(remainder=True)]
    [t.cancel() for t in t_followings]
    # print(folnet)

    # LiveStreams
    await q_followings.join()
    t_livestreams.cancel()

    await q_live_uids.join()
    [t.cancel() for t in t_total]



async def main():
    from datetime import datetime
    t = perf_counter()
    some_name = 'emilybarkiss'
    sample_sz = 300
    n_consumers = 100

    async with TwitchClient() as tc:
        streamer = Streamer(name=some_name, sample_sz=sample_sz)
        folnet = FollowNet(streamer_id=streamer.uid)
        ls = LiveStreamInfo()
        await run_v1(tc=tc, streamer=streamer, folnet=folnet, ls=ls, n_consumers=n_consumers)

        print(streamer)
        print(folnet)
        print(ls)

        print(f'{Col.magenta}🟊 N consumers: {n_consumers} {Col.end}')
        print(f'{Col.cyan}⏲ Total Time: {round(perf_counter() - t, 3)} sec {Col.end}')
        print(f'{Col.red}\t««« {datetime.now().strftime("%I:%M.%S %p")} »»» {Col.end}')


if __name__ == "__main__":
    asyncio.run(main())
