import asyncio
from collections import Counter
from time import perf_counter
from app.twitch_client_v2 import TwitchClient
from app.bot_detection import BotDetector
from app.streamer import Streamer

# Final shape
# TODO:  thought process here is to check 100 new live streams for occurence of 2 mutual followings and check finally
#  after collecting all followings

class FollowNetPipeline:
    MAX_BATCH_SZ = 100

    def __init__(self, tc: TwitchClient, streamer: Streamer, n_cons: int = 100):
        self.tc = tc
        self.streamer = streamer
        self.n_consumers = n_cons
        self.followings_counter = Counter()
        self.num_collected = 0
        self.num_skipped = 0
        self.checked_live_uids = set()
        self.unchecked_live_uids = set()
        self.live_streams = []
        self.num_live_stream_calls_to_twitch = 0



    async def consume_follower_samples(self, q_in, q_out, max_total_followings=150) -> None:
        """
        Fetches a follower id from the queue and collects a list of uids that they are following provided that they
        are not following more than max_total_followings.

        Args:
            q_in (asyncio.Queue):
                A queue of validated follower ids; used to fetch followings of followers.

            max_total_followings (int):
                Upper limit on the total followings for a given uid; avoids collecting 'followings' when a uid is
                following a large (bot-like) number of accounts.
        """

        while True:
            follower_id = await q_in.get()
            following_reply = await self.tc.get_full_n_followings(follower_id)
            if following_reply.get('total') < max_total_followings:
                foll_data = following_reply.get('data')
                self.followings_counter.update([following.get('to_id') for following in foll_data])
                self.num_collected += 1

                await self.check_live()


            else:
                # print(f'* Skipped: (uid: {follower_id:>9} | tot: {following_reply.get("total"):>4}) ')
                self.num_skipped += 1

            q_in.task_done()




    async def check_live(self, q_in: asyncio.Queue, min_mutual=2):
        while True:
            mutual_followings = q_in.get()

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
                #         await self.update_checked_live_streams(self.unchecked_live_uids)

            q_in.task_done()


    async def update_live_streams(self):
        batch_sz = self.MAX_BATCH_SZ
        if len(self.unchecked_live_uids) < batch_sz:
            batch_sz = len(self.unchecked_live_uids)
        candidates = [self.unchecked_live_uids.pop() for _ in range(0, batch_sz)]

        self.checked_live_uids.update(candidates)
        live_candidates = await self.tc.get_streams(channels=candidates)
        self.num_live_stream_calls_to_twitch += 1
        self.live_streams.extend(live_candidates)



    async def run_queue(self):
        # Create queues for pipeline
        q_followings = asyncio.Queue()
        q_live_status = asyncio.Queue()

        # Create tasks for pipeline
        await self.streamer.initialize()
        followers = asyncio.create_task(self.streamer.produce_follower_samples(q_followings, print_status=True))
        followings = [asyncio.create_task(self.consume_follower_samples(q_followings, q_live_status)) for _ in range(self.n_consumers)]
        live_status = 'TODO:  FILL THIS WITH A TASK'

        # Start the task pipeline
        await followers
        await q_followings.join()
        await q_live_status.join()

        # End all task queues
        for consumer in followings:
            consumer.cancel()

        print(f'  * Total Skipped: {self.num_skipped:>4}')
        print(f'  *    Total Kept: {self.num_collected:>4}')
        # Remove *this* streamer_id from counter
        self.followings_counter.pop(self.streamer.streamer_id, None)


        await self.update_live_streams()
        return self.followings_counter


async def main():
    some_name = 'emilybarkiss'
    sample_sz = 300
    n_consumers = 100
    n_consumers = 2
    await run_format(some_name, sample_sz, n_consumers)



async def run_format(some_name, sample_sz, n_consumers):
    tc = TwitchClient()
    streamer = Streamer(some_name, sample_sz)
    folnet = FollowNetPipeline(tc, streamer, n_cons=n_consumers)

    from app.colors import Col
    print(f'{Col.bold}{Col.yellow}\t<<<<< {some_name}  |  n={streamer.sample_sz} >>>>>{Col.end}')
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
