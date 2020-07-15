import asyncio
from collections import Counter
from time import perf_counter
from app.twitch_client_v2 import TwitchClient
from app.streamer import Streamer
from app.colors import Col
import logging

module_logger = logging.getLogger('follower_network.py')


class FollowNet:
    MIN_MUTUAL = 3

    def __init__(self, tc: TwitchClient, streamer_id):
        self.tc = tc
        self.streamer_id = streamer_id
        self._followings_counter = Counter()
        self.num_collected = 0
        self.num_skipped = 0


    def __str__(self, result='\n'):
        result += f'{Col.green}Follower Network: {Col.end}\n'
        result += f'{Col.white}  * Total Skipped: {self.num_skipped:>4}{Col.end}\n'
        result += f'{Col.white}  *    Total Kept: {self.num_collected:>4}{Col.end}\n'
        result += f'{Col.green}  Followings Counter (sz={len(self.followings_counter)}){Col.end}\n'
        result += f'     {self.followings_counter}\n'
        result += f'{Col.green}  Mutual Followings (sz={len(self.mutual_followings)}){Col.end}\n'
        result += f'     {self.mutual_followings}'

        return result


    @property
    def followings_counter(self) -> Counter:
        self._followings_counter.pop(self.streamer_id, None)
        return self._followings_counter


    @property
    def mutual_followings(self) -> set:
        return {uid for uid, count in self.followings_counter.items() if count >= self.MIN_MUTUAL}


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
    await streamer.produce_follower_samples(tc, q_out=q_followers)
    consumers = [asyncio.create_task(folnet.consume_follower_samples(q_in=q_followers)) for _ in range(n_consumers)]
    await q_followers.join()
    for c in consumers:
        c.cancel()


async def run_format(some_name, sample_sz):
    tc = TwitchClient()
    streamer = Streamer(name=some_name, sample_sz=sample_sz)
    await streamer(tc)
    folnet = FollowNet(tc=tc, streamer_id=streamer.streamer_uid)
    await run_queue(tc, streamer, folnet)

    print(streamer)
    print(folnet)
    await folnet.tc.close()


async def main():
    t = perf_counter()
    some_name = 'emilybarkiss'
    sample_sz = 300
    n_consumers = 60
    await run_format(some_name, sample_sz)

    print(f'{Col.magenta}🟊 N consumers: {n_consumers} {Col.end}')
    print(f'{Col.cyan}⏲ Total Time: {round(perf_counter() - t, 3)} sec {Col.end}')
    from datetime import datetime
    print(f'{Col.red}\t««« {datetime.now().strftime("%I:%M.%S %p")} »»» {Col.end}')


if __name__ == "__main__":
    asyncio.run(main())
