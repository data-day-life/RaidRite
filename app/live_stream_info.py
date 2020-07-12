import asyncio
from app.twitch_client_v2 import TwitchClient
from collections import Counter


class LiveStreamInfo:
    MAX_BATCH_SZ = 100

    def __init__(self, tc: TwitchClient=None):
        self.tc = tc or TwitchClient()
        self.live_streams = list()
        self.checked_live_uids = set()
        self.unchecked_live_uids = set()
        self.num_live_stream_calls_to_twitch = 0
        self.followings_counter = Counter()

    # TODO: Address Followings Counter
    async def check_live(self, min_mutual=2):
        mutual_followings = {uid for uid, count in self.followings_counter.items() if count >= min_mutual}
        if mutual_followings and len(mutual_followings) >= self.MAX_BATCH_SZ:
            self.unchecked_live_uids = mutual_followings - self.checked_live_uids
            # TODO: maybe use 'try' and 'finally' here instead?

            if len(self.unchecked_live_uids) >= self.MAX_BATCH_SZ:
                await self.update_live_streams()
            # Get remaining candidates after all batches of 100 were collected (unchecked + checked == mutual)
            # elif self.checked_live_uids:
            #     if self.unchecked_live_uids.union(self.checked_live_uids) == mutual_followings:
            #         print(f'Length of unchecked uids: {len(self.unchecked_live_uids)}')
            #
            # ^^^^^^^^^ DON'T FORGET TO DO THIS STEP IN THIS CLASS


    async def update_live_streams(self):
        batch_sz = self.MAX_BATCH_SZ
        if len(self.unchecked_live_uids) < batch_sz:
            batch_sz = len(self.unchecked_live_uids)
        candidates = [self.unchecked_live_uids.pop() for _ in range(0, batch_sz)]

        self.checked_live_uids.update(candidates)
        live_candidates = await self.tc.get_streams(channels=candidates)
        self.num_live_stream_calls_to_twitch += 1
        self.live_streams.extend(live_candidates)




async def main():
    some_name = 'emilybarkiss'
    sample_sz = 300
    n_consumers = 100
    n_consumers = 2
    # await run_format(some_name, sample_sz, n_consumers)



async def run_format(some_name, sample_sz, n_consumers):
    tc = TwitchClient()
    streamer_id = await tc.get_uid(some_name)
    folnet = FollowNetLiveStreams(streamer_id, tc, sample_sz=sample_sz, n_cons=n_consumers)

    from app.colors import Col
    print(f'{Col.bold}{Col.yellow}\t<<<<< {some_name}  |  n={sample_sz} >>>>>{Col.end}')
    t = perf_counter()

    # follower_ids = await folnet.produce_follower_samples(print_status=True)
    # print(f'Follower ID List:\n {follower_ids}')

    await folnet.run_queue()
    # print(folnet.followings_counter)
    # print(f'Counter length: {len(folnet.followings_counter)}')

    print(f'{Col.cyan}⏲ Total Time: {round(perf_counter() - t, 3)} sec {Col.end}')
    print(f'\t{Col.magenta}N consumers: {n_consumers}\n')

    print(f'{Col.green}Suggestions (sz={len(folnet.followings_counter)}){Col.end}')
    print(folnet.followings_counter)

    print(f'{Col.green}Live Stream Suggestions (sz={len(folnet.live_streams)}){Col.end}')
    print(folnet.live_streams)

    print(f'{Col.green}Num Unchecked for live status: (sz={len(folnet.unchecked_live_uids)}){Col.end}')
    print(folnet.live_streams)

    # trimmed_suggs = {uid: count for uid, count in folnet.followings_counter.items() if count >= 2}
    # print(f'{Col.yellow}Trimmed Suggestions (sz={len(trimmed_suggs)}){Col.end}')
    # print(trimmed_suggs)
    #
    # mutual =  {uid for uid, count in folnet.followings_counter.items() if count >= 2}
    # print(f'mutual: {mutual}')
    # print(f'len(mutual): {len(mutual)}')


    await folnet.tc.close()


if __name__ == "__main__":
    asyncio.run(main())
