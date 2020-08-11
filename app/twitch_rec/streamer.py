import asyncio
from app.twitch_rec.twitch_client import TwitchClient
from app.twitch_rec.bot_detection import BotDetector
from app.twitch_rec.colors import Col
from dataclasses import dataclass
from typing import List
import re


@dataclass
class Streamer:
    name:        str = None
    uid:         str = None
    prof_img:    str = None
    caster_type: str = None
    view_count:  int = None
    total_folls: int = -1
    valid:       bool = False


    @staticmethod
    def validate_name(name: str) -> str:
        if not name:
            raise ValueError('Provided name was empty ("") or "None".')
        # Strip any whitespace before matching to help the user; "Bob Ross" becomes a valid search
        matched = re.match(r"^(?!_)[a-zA-Z0-9_]{4,25}$", re.sub(r"\s+", "", name))
        if not matched:
            raise ValueError('Names may only contain 4-25 alpha-numeric characters (as well as "_") '
                             'and may not begin with "_" or contain any spaces.')

        return matched.string


    async def create(self, tc: TwitchClient, new_name: str = None):
        name = new_name or self.name
        try:
            valid_name = Streamer.validate_name(name)
            found = await tc.get_users(valid_name)
            found = found[0]
        except ValueError as err:
            print(err)
        except Exception as err:
            print(err)
        except IndexError:
            raise ValueError(f'No user named "{name}" could be found on Twitch.')
        else:
            self.name = found.display_name
            self.uid = found.id
            self.prof_img = found.profile_image
            self.caster_type = found.broadcaster_type
            self.view_count = found.view_count
            self.valid = True
        return self


    @property
    def display(self, result=''):
        try:
            result += f'{Col.bold}{Col.yellow}<<<<< Streamer:  {self.name}{Col.end}\n'
            result += f'\t\t{Col.yellow}🡲 uid: {self.uid}{Col.end}\n'
            result += f'{Col.white}  * Total followers: {self.total_folls}{Col.end}\n'
        except Exception as err:
            result += err

        return print(result)



class StreamerPipe:
    sanitized_follower_ids: List[str] = []

    def __init__(self, streamer: Streamer, sample_sz=300):
        if streamer is None:
            raise ValueError('Unable to create StreamerPipe; provided Streamer object was "None".')
        self.streamer = streamer
        self.sample_sz = sample_sz
        self.sanitized_follower_ids = list()
        self.bd = BotDetector()


    @property
    def display(self, result=''):
        result += f'{Col.bold}{Col.yellow}<<<<< Pipe: Streamer,  N={self.sample_sz}{Col.end}\n'
        result += f'{Col.white}  * {str(self.bd)}{Col.end}\n'
        result += f'{Col.yellow} > Follower ID List (sz={len(self.sanitized_follower_ids)}):{Col.end}\n'
        result += f'  {self.sanitized_follower_ids}\n'

        return print(result)


    async def __call__(self, tc: TwitchClient, q_out: asyncio.Queue = None):
        if self.streamer.valid:
            await self.produce_follower_ids(tc, q_out)
        else:
            raise AttributeError('Provided Streamer object has not been validated.')


    async def produce_follower_ids(self, tc: TwitchClient, q_out: asyncio.Queue = None):
        """
        For a valid uid, collect a list of sanitized_follower_ids while removing follower bots.  Batches of
        sanitized uids are placed into a given queue.

        Args:
            tc (TwitchClient):
                A twitch client; used to collect follower information for a uid.

            q_out (asyncio.Queue):
                The worker queue where follower ids are placed; fetches followings for the valid follower_id.

        Returns:
            A list of sanitized follower uids; length is not necessarily equal to sample_sz.
        """
        if not self.streamer.valid:
            raise AttributeError('Unable to produce follower ids: provided Streamer object has not been validated.')

        def put_queue(id_list):
            [q_out.put_nowait(foll_id) for foll_id in id_list]

        follower_reply = await tc.get_full_n_followers(self.streamer.uid, n_folls=self.sample_sz)
        next_cursor = follower_reply.get('cursor')
        self.streamer.total_folls = follower_reply.get('total', 0)

        # Sanitize first fetch, then sanitize remaining fetches
        all_sanitized_uids = self.bd.santize_foll_list(follower_reply.get('data'))
        if q_out:
            put_queue(all_sanitized_uids)

        while (len(all_sanitized_uids) < self.sample_sz) and next_cursor:
            params = [('after', next_cursor)]
            next_foll_reply = await tc.get_full_n_followers(self.streamer.uid, params=params)
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
    from time import perf_counter
    t = perf_counter()

    some_name = 'emilybarkiss'
    sample_sz = 300

    async with TwitchClient() as tc:
        streamer = await Streamer(some_name).create(tc)
        str_pipe = StreamerPipe(streamer, sample_sz=sample_sz)
        await str_pipe.produce_follower_ids(tc)

    streamer.display
    str_pipe.display
    print(f'{Col.cyan}⏲ Total Time: {round(perf_counter() - t, 3)} sec {Col.end}')


if __name__ == "__main__":
    asyncio.run(main())
