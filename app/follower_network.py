import asyncio
from collections import Counter
from time import perf_counter
from app.twitch_client_v2 import TwitchClient
from app.streamer import Streamer
from app.colors import Col
import logging

module_logger = logging.getLogger('follower_network.py')


class FollowNet:
    MIN_MUTUAL = 2
    MAX_FOLLOWINGS = 150
    BATCH_SZ = 100

    def __init__(self, streamer_id):
        self.streamer_id = streamer_id
        self._followings_counter = Counter()
        self.num_collected = 0
        self.num_skipped = 0
        self.batch_history = set()


    def __str__(self, result='\n'):
        result += f'{Col.green}<<<<< Follower Network {Col.end}\n'
        result += f'{Col.white}  * Total Skipped: {self.num_skipped:>4}{Col.end}\n'
        result += f'{Col.white}  *    Total Kept: {self.num_collected:>4}{Col.end}\n'
        result += f'{Col.green} > Followings Counter (sz={len(self.followings_counter)}){Col.end}\n'
        result += f'     {self.followings_counter}\n'
        result += f'{Col.green} > Mutual Followings (sz={len(self.mutual_followings)}){Col.end}\n'
        result += f'     {self.mutual_followings}\n'
        result += f'{Col.green} > Batch History (sz={len(self.batch_history)}){Col.end}\n'
        result += f'     {self.batch_history}\n'

        return result


    async def __aenter__(self):
        return self

    # TODO: this needs to be modified to work with q_out
    async def __aexit__(self, *args):
        self.new_candidate_batches(remainder=True)
        return


    @property
    def followings_counter(self) -> Counter:
        self._followings_counter.pop(self.streamer_id, None)
        return self._followings_counter


    @property
    def mutual_followings(self) -> set:
        return {uid for uid, count in self.followings_counter.items() if count >= self.MIN_MUTUAL}


    async def consume_follower_samples(self, tc: TwitchClient, q_in, q_out=None) -> None:
        """
        Fetches a follower id from the queue and collects a list of uids that they are following provided that they
        are not following more than max_total_followings.

        Args:
            tc (TwitchClient):
                An instance of a Twitch client

            q_in (asyncio.Queue):
                A queue of valid follower ids; used to fetch followings of followers.

            q_out (asyncio.Queue):
                A queue in which mutual followings are placed.
        """

        while True:
            follower_id = await q_in.get()
            if follower_id != 'DONE':
                following_reply = await tc.get_full_n_followings(follower_id)
                new_candidate_batches = self.update_followings(following_reply)
                if new_candidate_batches and q_out:
                    [q_out.put_nowait(batch) for batch in new_candidate_batches]

            else:
                print('DONE -- Saw "Done"')
                # await asyncio.sleep(1)
                # print(len(self.mutual_followings))
                # # DO LAST BATCH(ES)
                # print(f'Batch History (sz={len(self.batch_history)})')
                # print(f' * {self.batch_history}')
                # remaining_batches = self.new_candidate_batches(remainder=True)
                # print(f'Remaining Batches (sz={[len(b) for b in remaining_batches]})')
                # print(f' * {remaining_batches}')

                # if q_out:
                #     [q_out.put_nowait(batch) for batch in remaining_batches]

            q_in.task_done()


    def update_followings(self, following_reply, all_batches=False):
        if following_reply:
            if following_reply.get('total') <= self.MAX_FOLLOWINGS:
                foll_data = following_reply.get('data')
                self.followings_counter.update([following.get('to_id') for following in foll_data])
                self.num_collected += 1
            else:
                self.num_skipped += 1

        if all_batches:
            return self.new_candidate_batches(remainder=True)
        else:
            return self.new_candidate_batches(remainder=False)


    def new_candidate_batches(self, remainder=False):
        new_candidates = self.mutual_followings - self.batch_history
        batches = self.batchify(list(new_candidates), remainder)
        flat_candidates = batches
        if remainder and batches and isinstance(batches[0], list):
            flat_candidates = [uid for sublist in batches for uid in sublist]
        self.batch_history.update(flat_candidates)

        return batches


    def batchify(self, candidates, fetch_all=False):
        result = []
        if fetch_all:
            result = [candidates[i:i + self.BATCH_SZ] for i in range(0, len(candidates), self.BATCH_SZ)]
        elif len(candidates) > self.BATCH_SZ:
            result = candidates[:self.BATCH_SZ]

        return result


async def run_queue(tc: TwitchClient, streamer: Streamer, folnet: FollowNet, n_consumers=50):
    q_foll_ids = asyncio.Queue()

    # Initialize producers and consumers for processing
    producer = asyncio.create_task(streamer.produce_follower_samples(tc, q_out=q_foll_ids))
    consumers = [asyncio.create_task(folnet.consume_follower_samples(tc, q_in=q_foll_ids)) for _ in range(n_consumers)]
    # Block until producer and consumers are exhausted
    await asyncio.gather(producer)
    await q_foll_ids.join()
    # Cancel exhausted and idling consumers that are still waiting for items to appear in queue
    for c in consumers:
        c.cancel()

    # DO LAST BATCH(ES)
    folnet.new_candidate_batches(remainder=True)


async def run_format(some_name, sample_sz, n_consumers=50):
    async with TwitchClient() as tc:
        streamer = Streamer(name=some_name, sample_sz=sample_sz)
        folnet = FollowNet(streamer_id=streamer.uid)
        await run_queue(tc, streamer, folnet, n_consumers)
        print(streamer)
        print(folnet)


async def main():
    t = perf_counter()
    some_name = 'emilybarkiss'
    sample_sz = 350
    n_consumers = 100
    await run_format(some_name, sample_sz, n_consumers)

    print(f'{Col.magenta}🟊 N consumers: {n_consumers} {Col.end}')
    print(f'{Col.cyan}⏲ Total Time: {round(perf_counter() - t, 3)} sec {Col.end}')
    from datetime import datetime
    print(f'{Col.red}\t««« {datetime.now().strftime("%I:%M.%S %p")} »»» {Col.end}')


if __name__ == "__main__":
    asyncio.run(main())
