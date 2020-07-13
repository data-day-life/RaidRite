import asyncio
from collections import Counter
from time import perf_counter
from app.twitch_client_v2 import TwitchClient
from app.streamer import Streamer
import logging

module_logger = logging.getLogger('follower_network.py')

# Just gets followers followings and mutual followings


class FollowNet:

    def __init__(self, tc: TwitchClient, streamer_id):
        self.tc = tc
        self.streamer_id = streamer_id
        self.followings_counter = Counter()
        self.num_collected = 0
        self.num_skipped = 0


    @property
    def mutual_followings(self, min_mutual=2):
        return {uid for uid, count in self.followings_counter.items() if count >= min_mutual and
                uid != self.streamer_id}


    async def consume_follower_samples(self, q_in, q_out=None, max_followings=150) -> None:
        """
        Fetches a follower id from the queue and collects a list of uids that they are following provided that they
        are not following more than max_total_followings.

        Args:
            q_in (asyncio.Queue):
                A queue of validated follower ids; used to fetch followings of followers.

            q_out (asyncio.Queue):
                A queue in which mutual followings are placed.

            max_followings:
                Upper limit on the total followings for a given uid; avoids collecting 'followings' when a uid is
                following a large (bot-like) number of accounts.
        """
        while True:
            follower_id = await q_in.get()
            following_reply = await self.tc.get_full_n_followings(follower_id)
            if following_reply.get('total') < max_followings:
                foll_data = following_reply.get('data')
                self.followings_counter.update([following.get('to_id') for following in foll_data])
                self.num_collected += 1
                if q_out:
                    await q_out.put(self.mutual_followings)
            else:
                # print(f'* Skipped: (uid: {follower_id:>9} | tot: {following_reply.get("total"):>4}) ')
                self.num_skipped += 1

            q_in.task_done()



async def run_queue(tc: TwitchClient, streamer: Streamer, folnet: FollowNet, n_consumers=50):
    q_followers = asyncio.Queue()
    await streamer.produce_follower_samples(tc, q_out=q_followers, print_status=True)
    consumers = [asyncio.create_task(folnet.consume_follower_samples(q_in=q_followers)) for _ in range(n_consumers)]
    await q_followers.join()
    for c in consumers:
        c.cancel()

    print(f'  * Total Skipped: {folnet.num_skipped:>4}')
    print(f'  *    Total Kept: {folnet.num_collected:>4}')
    # Remove *this* streamer_id from counter
    folnet.followings_counter.pop(streamer.streamer_id, None)

    return streamer, folnet


async def run_format(some_name, sample_sz, n_consumers):
    from app.colors import Col
    t = perf_counter()

    tc = TwitchClient()
    streamer = Streamer(name=some_name, sample_sz=sample_sz)
    await streamer(tc)

    print(f'{Col.bold}{Col.yellow}\t<<<<< {some_name}  |  n={sample_sz} >>>>>{Col.end}')
    print(f'\t\t{Col.yellow}uid: {streamer.streamer_id}{Col.end}')
    print(f'\t{Col.magenta}N consumers: {n_consumers}')

    folnet = FollowNet(tc=tc, streamer_id=streamer.streamer_id)
    streamer, folnet = await run_queue(tc, streamer, folnet)

    print(f'{Col.cyan}⏲ Total Time: {round(perf_counter() - t, 3)} sec {Col.end}')
    print(f'{Col.green}Followings Counter (sz={len(folnet.followings_counter)}){Col.end}')
    print(f'   {folnet.followings_counter}')

    print(f'{Col.green}Mutual Followings (sz={len(folnet.mutual_followings)}){Col.end}')
    print(f'   {folnet.mutual_followings}')

    from datetime import datetime
    print(f'{Col.red}\t ««« {datetime.now().strftime("%I:%M.%S %p")} »»» {Col.red}')

    await folnet.tc.close()


async def main():
    some_name = 'stroopc'
    sample_sz = 300
    n_consumers = 50
    await run_format(some_name, sample_sz, n_consumers)


if __name__ == "__main__":
    asyncio.run(main())
