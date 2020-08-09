import asyncio
from time import perf_counter
from typing import List, Dict
from dateutil.parser import parse as dt_parse
from datetime import datetime as datetime
from pytz import utc
from app.twitch_rec.twitch_client import TwitchClient
from app.twitch_rec.streamer import StreamerPipe
from app.twitch_rec.follower_network import FollowNetPipe, FollowerNetwork
from app.twitch_rec.colors import Col
from dataclasses import dataclass, field


@dataclass
class LiveStreams:
    data:       dict = field(default_factory={})
    lang:       str = 'en'
    init_time:  datetime = field(default=datetime.now(utc))


    @staticmethod
    def dictify_list(livestream_list: list) -> dict:
        return {stream.get('user_id'): stream for stream in livestream_list if livestream_list}


    @staticmethod
    def list_apply_stream_duration(livestream_list: list, base_time: datetime) -> list:
        [stream.update(LiveStreams.parse_duration(stream.get('started_at'), base_time))
         for stream in livestream_list]
        return livestream_list


    @staticmethod
    def parse_duration(twitch_time: str, base_time: datetime) -> dict:
        diff = (base_time - dt_parse(twitch_time)).total_seconds()
        result = {'stream_duration': f'{int(diff // 3600)}hr {int((diff % 3600) // 60)}min'}
        return result


    def list_filter_language(self, livestream_list: list, lang: str = None) -> list:
        return [ls for ls in livestream_list if ls.get('language') == (lang or self.lang)]


    def add_uid_tot_followers(self, uid: str, total_followers):
        if self.data.get(uid, None):
            self.data[uid].update({'total_followers': total_followers})


    def update_from_list(self, livestream_list: list, initial_time=None):
        base_time = initial_time or self.init_time
        if livestream_list:
            # livestream_list = self.list_filter_language(livestream_list)
            livestream_list = LiveStreams.list_apply_stream_duration(livestream_list, base_time)
            ls_dict = LiveStreams.dictify_list(livestream_list)
            self.data.update(ls_dict)


    def get(self, data_key) -> dict:
        return self.data.get(data_key)


    @property
    def total_followers(self) -> list:
        return [{uid: uid.get('total_followers')} for uid in self.data]



class LiveStreamPipe:
    live_streams:       LiveStreams
    fetched_batches:    List[str] = []
    num_ls_reqs:        int = 0


    def __init__(self, live_streams: LiveStreams = None, lang_filter: str = 'en') -> None:
        self.live_streams = live_streams or LiveStreams(lang=lang_filter)


    def __repr__(self):
        return (f'{self.__class__.__name__}('
                f'{self.num_ls_reqs!r}, {self.fetched_batches!r}, {self.live_streams!r})')


    @property
    def show(self, result=''):
        result += f'{Col.orange}<<<<< Pipe: Live Stream {Col.end}\n'
        result += f'{Col.white}  * Calls to Twitch: {self.num_ls_reqs}{Col.end}\n'
        result += f'{Col.orange} > Total Fetched Batches (sz={len(self.fetched_batches)}):{Col.end}\n'
        result += f'     {self.fetched_batches}\n'
        result += f'{Col.orange} > Live Streams (sz={len(self.live_streams.data)}):{Col.end}\n'
        result += f'     {self.live_streams}\n'
        tot_followers = [{f'uid: {uid}': f'tot: {details.get("total_followers")}'} for uid, details in self.live_streams.data.items()]
        result += f'{Col.orange} > Tot. Followers, Live Streams (sz={len(tot_followers)}):{Col.end}\n'
        result += f'     {tot_followers}\n'
        return print(result)


    async def __call__(self, tc: TwitchClient, q_in_followings: asyncio.Queue, q_out: asyncio.Queue = None, n_cons=50):
        q_live_uids = asyncio.Queue()
        t_livestreams = asyncio.create_task(self.produce_live_streams(tc, q_in=q_in_followings, q_out=q_live_uids))
        t_total = [asyncio.create_task(
            self.consume_live_streams(tc, q_in=q_live_uids)) for _ in range(n_cons)]

        await q_in_followings.join()
        t_livestreams.cancel()

        await q_live_uids.join()
        [t.cancel() for t in t_total]


    async def fetch_live_streams(self, tc: TwitchClient, candidates) -> list:
        self.num_ls_reqs += 1
        return await tc.get_streams(channels=candidates)


    async def produce_live_streams(self, tc: TwitchClient, q_in: asyncio.Queue, q_out: asyncio.Queue = None):
        while True:
            candidate_batch = await q_in.get()
            self.fetched_batches.extend(candidate_batch)
            found_live_streams_list = await self.fetch_live_streams(tc, candidate_batch)
            if found_live_streams_list := self.live_streams.list_filter_language(found_live_streams_list):
                self.live_streams.update_from_list(found_live_streams_list)
                if q_out:
                    [q_out.put_nowait(stream.get('user_id')) for stream in found_live_streams_list]

            q_in.task_done()


    async def consume_live_streams(self, tc: TwitchClient, q_in: asyncio.Queue, q_out: asyncio.Queue = None):
        while True:
            live_streamer_uid = await q_in.get()
            total_followers = await tc.get_total_followers(int(live_streamer_uid))
            self.live_streams.get(live_streamer_uid).update({'total_followers': total_followers})

            if q_out:
                pass
            q_in.task_done()




async def run_v2(tc: TwitchClient, streamer: StreamerPipe, folnet_pipe: FollowNetPipe, ls_pipe: LiveStreamPipe, n_consumers=50):
    print('\n\n********** Run V2 ********** ')
    q_foll_ids = asyncio.Queue()
    q_followings = asyncio.Queue()
    q_live_uids = asyncio.Queue()

    t_prod = asyncio.create_task(streamer.produce_follower_ids(tc, q_out=q_foll_ids))
    t_followings = [asyncio.create_task(
        folnet_pipe.produce_followed_ids(tc, q_in=q_foll_ids, q_out=q_followings)) for _ in range(n_consumers)]
    # t_livestreams = asyncio.create_task(self.produce_live_streams(tc, q_in=q_followings, q_out=q_live_uids))
    # t_total = [asyncio.create_task(
    #     self.consume_live_streams(tc, q_in=q_live_uids)) for _ in range(n_consumers//2)]

    # Streamer: follower ids
    await asyncio.gather(t_prod)
    # print(streamer)

    # Folnet: follower's followings
    await q_foll_ids.join()

    # task creation must follow q_foll_ids.join() b/c the join produces q_followings
    t_ls = asyncio.create_task(ls_pipe(tc, q_in_followings=q_followings, n_cons=n_consumers // 2))
    [q_followings.put_nowait(batch) for batch in folnet_pipe.new_candidate_batches(remainder=True)]
    [t.cancel() for t in t_followings]
    print(folnet_pipe)

    # LiveStreams
    await q_followings.join()
    # print(self)

    await q_live_uids.join()

    # task creation must follow q_foll_ids.join() b/c the join produces q_followings
    # t_ls = asyncio.create_task(self.__call__(tc, q_in_followings=q_followings))
    await asyncio.gather(t_ls)
    t_ls.cancel()



async def run_v1(tc: TwitchClient, streamer: StreamerPipe, folnet_pipe: FollowNetPipe, ls_pipe: LiveStreamPipe, n_consumers=50):
    print('\n\n********** Run V1 ********** ')
    q_foll_ids = asyncio.Queue()
    q_followings = asyncio.Queue()
    q_live_uids = asyncio.Queue()

    t_prod = asyncio.create_task(streamer.produce_follower_ids(tc, q_out=q_foll_ids))
    t_followings = [asyncio.create_task(
        folnet_pipe.produce_followed_ids(tc, q_in=q_foll_ids, q_out=q_followings)) for _ in range(n_consumers)]
    t_livestreams = asyncio.create_task(ls_pipe.produce_live_streams(tc, q_in=q_followings, q_out=q_live_uids))
    t_total = [asyncio.create_task(
        ls_pipe.consume_live_streams(tc, q_in=q_live_uids)) for _ in range(n_consumers // 2)]

    # Streamer: follower ids
    await asyncio.gather(t_prod)
    # print(streamer)

    # Folnet: follower's followings
    await q_foll_ids.join()
    [q_followings.put_nowait(batch) for batch in folnet_pipe.new_candidate_batches(remainder=True)]
    [t.cancel() for t in t_followings]
    # print(folnet)

    # LiveStreams
    await q_followings.join()
    t_livestreams.cancel()

    await q_live_uids.join()
    [t.cancel() for t in t_total]
    # print(ls)



async def main():
    from datetime import datetime
    t = perf_counter()
    some_name = 'emilybarkiss'
    sample_sz = 300
    n_consumers = 100

    async with TwitchClient() as tc:
        streamer = StreamerPipe(name=some_name, sample_sz=sample_sz)
        folnet = FollowerNetwork(streamer_id=streamer.uid)
        folnet_pipe = FollowNetPipe(folnet)
        live_streams = LiveStreams()
        ls_pipe = LiveStreamPipe(live_streams)
        await run_v1(tc=tc, streamer=streamer, folnet_pipe=folnet_pipe, ls_pipe=ls_pipe, n_consumers=n_consumers)

        print(streamer)
        folnet_pipe.print
        ls_pipe.show

        print(f'{Col.magenta}🟊 N consumers: {n_consumers} {Col.end}')
        print(f'{Col.cyan}⏲ Total Time: {round(perf_counter() - t, 3)} sec {Col.end}')
        print(f'{Col.red}\t««« {datetime.now().strftime("%I:%M.%S %p")} »»» {Col.end}')


if __name__ == "__main__":
    asyncio.run(main())
