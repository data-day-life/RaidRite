import asyncio
from app.twitch_rec.twitch_client import TwitchClient
from app.twitch_rec.streamer import StreamerPipe
from app.twitch_rec.follower_network import FollowNetPipe, FollowerNetwork
from app.twitch_rec.live_stream_info import LiveStreamPipe, LiveStreams


class PipelineBuilder:

    def __init__(self, streamer: StreamerPipe, folnet: FollowerNetwork, live_streams: LiveStreams) -> None:
        self.streamer_pipe = streamer
        self.folnet_pipe = FollowNetPipe(folnet)
        self.live_stream_pipe = LiveStreamPipe(live_streams)


    @classmethod
    def from_name(cls, streamer_name: str, sample_sz: int = 300):
        streamer = StreamerPipe(name=streamer_name, sample_sz=sample_sz)
        folnet = FollowerNetwork(streamer.uid)
        live_streams = LiveStreams()

        return cls(streamer, folnet, live_streams)


    async def __call__(self, tc: TwitchClient, n_consumers: int):
        q_foll_ids = asyncio.Queue()
        q_followings = asyncio.Queue()
        q_live_uids = asyncio.Queue()

        t_prod = asyncio.create_task(self.streamer_pipe(tc, q_out=q_foll_ids))
        t_followings = [asyncio.create_task(
            self.folnet_pipe.produce_followed_ids(tc, q_in=q_foll_ids, q_out=q_followings)) for _ in range(n_consumers)]
        t_livestreams = asyncio.create_task(
            self.live_stream_pipe.produce_live_streams(tc, q_in=q_followings, q_out=q_live_uids))
        t_total = [asyncio.create_task(
            self.live_stream_pipe.consume_live_streams(tc, q_in=q_live_uids)) for _ in range(n_consumers // 2)]

        # Streamer: follower ids
        await asyncio.gather(t_prod)

        # Folnet: follower's followings
        await q_foll_ids.join()
        [q_followings.put_nowait(batch) for batch in self.folnet_pipe.new_candidate_batches(remainder=True)]
        [t.cancel() for t in t_followings]

        # LiveStreams
        await q_followings.join()
        t_livestreams.cancel()

        await q_live_uids.join()
        [t.cancel() for t in t_total]


async def main():
    from app.twitch_rec.colors import Col
    from datetime import datetime
    from time import perf_counter
    t = perf_counter()

    some_name = 'emilybarkiss'
    sample_sz = 350
    n_consumers = 100

    streamer = StreamerPipe('emilybarkiss', sample_sz=sample_sz)
    folnet = FollowerNetwork(streamer.uid)
    live_streams = LiveStreams()
    pipeline = PipelineBuilder(streamer, folnet, live_streams)
    async with TwitchClient() as tc:
        await pipeline(tc, n_consumers)

    print(pipeline.streamer_pipe)
    pipeline.folnet_pipe.display
    pipeline.live_stream_pipe.display

    print(f'{Col.magenta}🟊 N consumers: {n_consumers} {Col.end}')
    print(f'{Col.cyan}⏲ Total Time: {round(perf_counter() - t, 3)} sec {Col.end}')
    print(f'{Col.red}\t««« {datetime.now().strftime("%I:%M.%S %p")} »»» {Col.end}')


if __name__ == "__main__":
    asyncio.run(main())
