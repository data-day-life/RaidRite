import asyncio
from app.twitch_client_v2 import TwitchClient
from app.bot_detection import BotDetector
from time import perf_counter



class Streamer:

    def __init__(self, tc: TwitchClient() = None, name=None, streamer_id=None, sample_sz=300):
        self.tc = tc or TwitchClient()
        self.bd = BotDetector()
        self.name = name
        self.streamer_id = streamer_id
        self.sample_sz = sample_sz
        self.total_followers = None


    async def initialize(self):
        if self.streamer_id:
            return
        if not self.name:
            raise AttributeError('Streamer name not set; unable to get_streamer_id()')
        try:
            self.streamer_id = await self.tc.get_uid(self.name)
        except IndexError:
            print(f'Streamer named "{self.name}" not found.')
            raise AttributeError('Streamer uid not set.')


    async def produce_follower_samples(self, q_out: asyncio.Queue = None, print_status: bool = False):
        """
        For a valid streamer_id, collect a list of follower_ids while removing follower bots.  Batches of sanitized
        uids are placed into a given queue.

        Args:
            q_out (asyncio.Queue):
                The worker queue that fetches followings for the validated follower_id.

            print_status (bool):
                Prints information about total followers, total skipped, and total kept (sanitized).

        Returns:
            A list of sanitized follower uids; length is not necessarily equal to sample_sz.
        """
        if not self.streamer_id:
            await self.initialize()

        async def put_queue(id_list):
            [await q_out.put(foll_id) for foll_id in id_list]

        follower_reply = await self.tc.get_full_n_followers(self.streamer_id, n_folls=self.sample_sz)
        next_cursor = follower_reply.get('cursor')
        self.total_followers = follower_reply.get('total', 0)

        # Sanitized first fetch, then sanitize remaining fetches
        all_sanitized_uids = await self.bd.santize_foll_list(follower_reply.get('data'))
        if q_out:
            await put_queue(all_sanitized_uids)

        while (len(all_sanitized_uids) < self.sample_sz) and next_cursor:
            # print(f'Total sanitized uids: {len(all_sanitized_uids)}')
            params = [('after', next_cursor)]
            next_foll_reply = await self.tc.get_full_n_followers(self.streamer_id, params=params)
            next_cursor = next_foll_reply.get('cursor')
            next_sanitized_uids = await self.bd.santize_foll_list(next_foll_reply.get('data'))
            all_sanitized_uids.extend(next_sanitized_uids)
            if q_out:
                await put_queue(next_sanitized_uids)

        if print_status:
            print(f'> Removed {self.bd.total_removed} potential follower bots total.')
            print(f'> Total sanitized uids: {len(all_sanitized_uids)}')
            print(f'> Total followers: {self.total_followers}')

        return all_sanitized_uids


async def main():
    tc = TwitchClient()
    some_name = 'emilybarkiss'
    sample_sz = 300
    streamer = Streamer(tc=tc, name=some_name, sample_sz=sample_sz)

    from app.colors import Col
    print(f'{Col.bold}{Col.yellow}\t<<<<< {some_name}  |  n={streamer.sample_sz} >>>>>{Col.end}')
    t = perf_counter()

    follower_ids = await streamer.produce_follower_samples(print_status=True)
    print(f'{Col.cyan}⏲ Total Time: {round(perf_counter() - t, 3)} sec {Col.end}')

    print(f'Follower ID List:\n {follower_ids}')
    print(f'Length of Foll List:\n {len(follower_ids)}')

    await tc.close()



if __name__ == "__main__":
    asyncio.run(main())