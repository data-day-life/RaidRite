import asyncio
from app.twitch_client_v2 import TwitchClient
from app.streamer import Streamer
from app.follower_network import FollowNet
from time import perf_counter
from app.colors import Col


class LiveStreamInfo:
    MAX_BATCH_SZ = 100

    def __init__(self, tc: TwitchClient = None):
        self.tc = tc or TwitchClient()
        self.live_streams = list()
        self.checked_live_uids = set()
        self.unchecked_live_uids = set()
        self.num_live_stream_calls_to_twitch = 0
        self.last_mutual_followings = None


    def __str__(self, result='\n'):
        result += f'{Col.orange}<<<<< Live Stream Info {Col.end}\n'
        result += f'{Col.white}  * Calls to Twitch: {self.num_live_stream_calls_to_twitch}{Col.end}\n'
        result += f'{Col.orange} > Live Streams (sz={len(self.live_streams)}):{Col.end}\n'
        result += f'     {self.live_streams}\n'
        result += f'{Col.orange} > Unchecked Live UIDs (sz={len(self.unchecked_live_uids)}):{Col.end}\n'
        result += f'     {self.unchecked_live_uids}\n'
        result += f'{Col.orange} > Checked Live UIDs (sz={len(self.checked_live_uids)}):{Col.end}\n'
        result += f'     {self.checked_live_uids}\n'
        result += f'{Col.orange} > Last Mutual Followings (sz={len(self.last_mutual_followings)}):{Col.end}\n'
        result += f'     {self.last_mutual_followings}'

        return result


    @staticmethod
    def filter_language(live_streams, lang='en'):
        return [ls for ls in live_streams if ls.get('language', None) == lang]


    async def consume_mutual_followings(self, q_in: asyncio.Queue, q_out: asyncio.Queue = None):
        while True:
            mutual_followings = await q_in.get()
            self.last_mutual_followings = mutual_followings
            await self.check_live(mutual_followings)

            if q_out:
                pass
            q_in.task_done()


    async def check_live(self, mutual_followings):
        if mutual_followings and len(mutual_followings) >= self.MAX_BATCH_SZ:
            self.unchecked_live_uids = mutual_followings - self.checked_live_uids

            if len(self.unchecked_live_uids) >= self.MAX_BATCH_SZ:
                await self.update_live_streams()


    async def update_live_streams(self):
        batch_sz = self.MAX_BATCH_SZ
        if len(self.unchecked_live_uids) < batch_sz:
            batch_sz = len(self.unchecked_live_uids)
        candidates = [self.unchecked_live_uids.pop() for _ in range(0, batch_sz)]

        self.checked_live_uids.update(candidates)
        live_candidates = await self.tc.get_streams(channels=candidates)
        self.live_streams.extend(live_candidates)
        self.num_live_stream_calls_to_twitch += 1


async def run_queue(tc: TwitchClient, streamer: Streamer, folnet: FollowNet, ls: LiveStreamInfo, n_consumers=50):
    q_followers = asyncio.Queue()
    q_followings = asyncio.Queue()
    await streamer.produce_follower_samples(tc, q_out=q_followers)

    consume_followings = [asyncio.create_task(
        folnet.consume_follower_samples(q_in=q_followers, q_out=q_followings)) for _ in range(n_consumers)]
    consume_livestreams = asyncio.create_task(ls.consume_mutual_followings(q_followings))

    await q_followers.join()
    await q_followings.join()

    for c in consume_followings:
        c.cancel()
    consume_livestreams.cancel()


async def run_format(some_name, sample_sz, n_consumers):
    tc = TwitchClient()
    streamer = Streamer(name=some_name, sample_sz=sample_sz)
    await streamer(tc)
    folnet = FollowNet(tc, streamer.streamer_uid)
    ls = LiveStreamInfo(tc)
    await run_queue(tc, streamer, folnet, ls, n_consumers)

    print(streamer)
    print(folnet)
    print(ls)
    await tc.close()


async def main():
    t = perf_counter()
    some_name = 'emilybarkiss'
    sample_sz = 300
    n_consumers = 100
    await run_format(some_name, sample_sz, n_consumers)

    print(f'{Col.magenta}🟊 N consumers: {n_consumers} {Col.end}')
    print(f'{Col.cyan}⏲ Total Time: {round(perf_counter() - t, 3)} sec {Col.end}')
    from datetime import datetime
    print(f'{Col.red}\t««« {datetime.now().strftime("%I:%M.%S %p")} »»» {Col.end}')


if __name__ == "__main__":
    asyncio.run(main())
