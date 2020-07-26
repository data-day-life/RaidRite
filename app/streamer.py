import asyncio
from app.twitch_client_v2 import TwitchClient
from app.bot_detection import BotDetector
from time import perf_counter
from app.colors import Col


class Streamer:

    def __init__(self, name=None, streamer_id=None, sample_sz=300):
        self.name = name
        self.streamer_uid = streamer_id
        self.sample_sz = sample_sz
        self.total_followers = None
        self.sanitized_follower_ids = list()
        self.bd = BotDetector()

        if self.streamer_uid is None and self.name is None:
            raise AttributeError('Neither streamer_uid name nor uid were provided')


    def __str__(self, result='\n'):
        result += f'{Col.bold}{Col.yellow}<<<<< {self.name}  |  n={self.sample_sz} >>>>>{Col.end}\n'
        result += f'\t\t{Col.yellow}🡲 uid: {self.streamer_uid}{Col.end}\n'
        result += f'{Col.white}  * Total followers: {self.total_followers}{Col.end}\n'
        result += f'{Col.white}  * {str(self.bd)}{Col.end}\n'
        result += f'{Col.yellow} > Follower ID List (sz={len(self.sanitized_follower_ids)}):{Col.end}\n'
        result += f'  {self.sanitized_follower_ids}'

        return result


    async def __call__(self, tc: TwitchClient):
        if self.streamer_uid:
            return
        if not self.name:
            raise AttributeError('Streamer name not set; unable to get_streamer_id()')
        try:
            self.streamer_uid = await tc.get_uid(self.name)
        except IndexError:
            print(f'Streamer named "{self.name}" not found.')
            raise AttributeError('Streamer uid not set.')


    async def produce_follower_samples(self, tc: TwitchClient, q_out: asyncio.Queue = None):
        """
        For a valid streamer_uid, collect a list of sanitized_follower_ids while removing follower bots.  Batches of
        sanitized uids are placed into a given queue.

        Args:
            tc (TwitchClient):
                A twitch client; used to collect follower information for a streamer_uid.

            q_out (asyncio.Queue):
                The worker queue where follower ids are placed; fetches followings for the validated follower_id.

        Returns:
            A list of sanitized follower uids; length is not necessarily equal to sample_sz.
        """

        def put_queue(id_list):
            [q_out.put_nowait(foll_id) for foll_id in id_list]

        follower_reply = await tc.get_full_n_followers(self.streamer_uid, n_folls=self.sample_sz)
        next_cursor = follower_reply.get('cursor')
        self.total_followers = follower_reply.get('total', 0)

        # Sanitize first fetch, then sanitize remaining fetches
        all_sanitized_uids = self.bd.santize_foll_list(follower_reply.get('data'))
        if q_out:
            put_queue(all_sanitized_uids)

        while (len(all_sanitized_uids) < self.sample_sz) and next_cursor:
            params = [('after', next_cursor)]
            next_foll_reply = await tc.get_full_n_followers(self.streamer_uid, params=params)
            next_cursor = next_foll_reply.get('cursor')
            next_sanitized_uids = self.bd.santize_foll_list(next_foll_reply.get('data'))
            all_sanitized_uids.extend(next_sanitized_uids)
            if q_out:
                put_queue(next_sanitized_uids)

        if q_out:
            q_out.put_nowait('DONE')

        self.sanitized_follower_ids = all_sanitized_uids
        return self.sanitized_follower_ids


async def main():
    t = perf_counter()
    some_name = 'emilybarkiss'
    sample_sz = 300

    streamer = Streamer(name=some_name, sample_sz=sample_sz)
    async with TwitchClient() as tc:
        await streamer(tc)
        await streamer.produce_follower_samples(tc)

    print(streamer)
    print(f'{Col.cyan}⏲ Total Time: {round(perf_counter() - t, 3)} sec {Col.end}')


if __name__ == "__main__":
    asyncio.run(main())
