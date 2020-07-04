import asyncio
from collections import Counter
from time import perf_counter
from app.twitch_client_v2 import TwitchClient
from app.bot_detection import BotDetector


class FollowNet:

    def __init__(self, streamer_id, tc: TwitchClient, sample_sz=300, n_cons: int = 100):
        self.tc = tc
        self.queue = asyncio.Queue()
        self.n_consumers = n_cons
        self.sample_sz = sample_sz
        self.streamer_id = streamer_id
        self.total_followers = 0
        self.followings_counter = Counter()
        self.num_collected = 0
        self.num_skipped = 0


    async def produce_follower_samples(self, print_status: bool = False):
        """
        Given a valid streamer_id, collect a list of follower_ids while removing follower bots.  Batches of sanitized
        uids are placed into a queue.

        Args:
            print_status (bool):
                Prints information about total followers, total skipped, and total kept (sanitized).

        Returns:
            A list of sanitized follower uids; length is not necessarily equal to sample_sz.
        """
        if not self.streamer_id:
            raise AttributeError('Streamer uid not set.')

        async def put_queue(id_list):
            [await self.queue.put(foll_id) for foll_id in id_list]

        follower_reply = await self.tc.get_full_n_followers(self.streamer_id, n_folls=self.sample_sz)
        next_cursor = follower_reply.get('cursor')
        self.total_followers = follower_reply.get('total', 0)

        bd = BotDetector()
        all_sanitized_uids = await bd.santize_foll_list(follower_reply.get('data'))
        await put_queue(all_sanitized_uids)

        while next_cursor and (len(all_sanitized_uids) < self.sample_sz):
            # print(f'Total sanitized uids: {len(all_sanitized_uids)}')
            params = [('after', next_cursor)]
            next_foll_reply = await self.tc.get_full_n_followers(self.streamer_id, self.sample_sz, params=params)
            next_sanitized_uids = await bd.santize_foll_list(next_foll_reply.get('data'))
            await put_queue(next_sanitized_uids)
            all_sanitized_uids.extend(next_sanitized_uids)
            next_cursor = next_foll_reply.get('cursor')

        if print_status:
            print(f'> Removed {bd.total_removed} potential follower bots total.')
            print(f'> Total sanitized uids: {len(all_sanitized_uids)}')
            print(f'> Total followers: {self.total_followers}')

        return all_sanitized_uids


    async def consume_follower_samples(self, max_total_followings=150) -> None:
        """
        Fetches a follower id from the queue and collects a list of uids that they are following provided that they
        are not following more than max_total_followings.

        Args:
            max_total_followings:
                Upper limit on the total followings for a given uid; avoids collecting 'followings' when a uid is
                following a large (bot-like) number of accounts.
        """
        while True:
            follower_id = await self.queue.get()
            following_reply = await self.tc.get_full_n_followings(follower_id)
            if following_reply.get('total') < max_total_followings:
                foll_data = following_reply.get('data')
                self.followings_counter.update([following.get('to_id') for following in foll_data])
                self.num_collected += 1
            else:
                # print(f'* Skipped: (uid: {follower_id:>9} | tot: {following_reply.get("total"):>4}) ')
                self.num_skipped += 1

            self.queue.task_done()


    async def run_queue(self):
        consumers = [asyncio.create_task(self.consume_follower_samples()) for _ in range(self.n_consumers)]
        await self.produce_follower_samples(print_status=True)
        await self.queue.join()
        for c in consumers:
            c.cancel()
        print(f'  * Total Skipped: {self.num_skipped:>4}')
        print(f'  *    Total Kept: {self.num_collected:>4}')
        # Remove *this* streamer_id from counter
        self.followings_counter.pop(self.streamer_id, None)

        return self.followings_counter


async def main():
    some_name = 'stroopc'
    sample_sz = 300
    n_consumers = 100
    await run_format(some_name, sample_sz, n_consumers)



async def run_format(some_name, sample_sz, n_consumers):
    tc = TwitchClient()
    streamer_id = await tc.get_uid(some_name)
    folnet = FollowNet(streamer_id, tc, sample_sz=sample_sz, n_cons=n_consumers)

    from app.colors import Col
    print(f'{Col.bold}{Col.yellow}\t<<<<< {some_name}  |  n={sample_sz} >>>>>{Col.end}')
    t = perf_counter()

    # follower_ids = await folnet.produce_follower_samples(print_status=True)
    # print(f'Follower ID List:\n {follower_ids}')

    await folnet.run_queue()
    # print(folnet.followings_count)
    # print(f'Counter length: {len(rec.followings_count)}')

    print(f'{Col.cyan}⏲ Total Time: {round(perf_counter() - t, 3)} sec {Col.end}')
    print(f'\t{Col.magenta}N consumers: {n_consumers}\n')

    print(f'{Col.green}Suggestions (sz={len(folnet.followings_counter)}){Col.end}')
    print(folnet.followings_counter)

    trimmed_suggs = {uid: count for uid, count in folnet.followings_counter.items() if count >= 2}
    print(f'{Col.green}Trimmed Suggestions (sz={len(trimmed_suggs)}){Col.end}')
    print(trimmed_suggs)

    await folnet.tc.close()


if __name__ == "__main__":
    asyncio.run(main())
