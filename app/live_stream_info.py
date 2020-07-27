import asyncio
from app.twitch_client_v2 import TwitchClient
from app.streamer import Streamer
from app.follower_network import FollowNet
from time import perf_counter
from app.colors import Col


class LiveStreamInfo:
    MAX_BATCH_SZ = 100

    def __init__(self):
        self.live_streams = list()
        self.num_live_stream_calls_to_twitch = 0


    def __str__(self, result='\n'):
        result += f'{Col.orange}<<<<< Live Stream Info {Col.end}\n'
        result += f'{Col.white}  * Calls to Twitch: {self.num_live_stream_calls_to_twitch}{Col.end}\n'
        result += f'{Col.orange} > Live Streams (sz={len(self.live_streams)}):{Col.end}\n'
        result += f'     {self.live_streams}\n'

        return result


    @staticmethod
    def filter_language(live_streams, lang='en'):
        return [ls for ls in live_streams if ls.get('language', None) == lang]


    async def consume_candidate_batches(self, tc: TwitchClient, q_in: asyncio.Queue, q_out: asyncio.Queue = None):
        while True:
            candidate_batch = await q_in.get()
            live_streams = await self.update_live_streams(tc, candidate_batch, filter_lang=True, lang='en')

            if q_out:
                pass
            q_in.task_done()


    async def update_live_streams(self, tc: TwitchClient, candidates, filter_lang=True, lang='en'):
        live_candidates = await tc.get_streams(channels=candidates)
        if filter_lang:
            live_candidates = self.filter_language(live_candidates, lang=lang)
        self.live_streams.extend(live_candidates)
        self.num_live_stream_calls_to_twitch += 1

        return live_candidates


async def run_queue(tc: TwitchClient, streamer: Streamer, folnet: FollowNet, ls: LiveStreamInfo, n_consumers=50):
    q_foll_ids = asyncio.Queue()
    q_followings = asyncio.Queue()

    # Initialize producers and consumers for processing
    t_foll_ids = asyncio.create_task(streamer.produce_follower_samples(tc, q_out=q_foll_ids))
    t_followings = [asyncio.create_task(
        folnet.consume_follower_samples(tc, q_in=q_foll_ids, q_out=q_followings)) for _ in range(n_consumers)]
    t_livestreams = asyncio.create_task(ls.consume_candidate_batches(tc, q_followings))

    # Block until producer and consumers are exhausted
    await asyncio.gather(t_foll_ids)
    await q_foll_ids.join()
    await q_followings.join()

    # Cancel exhausted and idling consumers that are still waiting for items to appear in queue
    for task in t_followings:
        task.cancel()
    t_livestreams.cancel()


async def run_format(some_name, sample_sz, n_consumers):
    tc = TwitchClient()
    streamer = Streamer(name=some_name, sample_sz=sample_sz)
    await streamer(tc)
    folnet = FollowNet(streamer.uid)
    ls = LiveStreamInfo()
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
