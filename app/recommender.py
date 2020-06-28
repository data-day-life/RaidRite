from app.twitch_client_v2 import TC
import asyncio
from collections import Counter


streambots = ['nightbot', 'streamelements']


class Recommender:

    def __init__(self):
        self.loop = asyncio.get_event_loop()
        self.tc = TC(loop=self.loop)
        self.followings_count = Counter()


    async def gen_suggestions(self, streamer_name, sample_sz=300):
        streamer_id = await self.tc.get_uids(streamer_name)
        if not streamer_id:
            return {}

        # TODO: ? Check if stream is live, if true then Prioritize Active viewers -- ignore streambots

        # Get n follower uids
        followers = self.tc.get_fols(streamer_id, limit=sample_sz)


        return await self.tc.get_users(streamer_name)



async def main():
    rec = Recommender()
    some_name = 'stroopc'
    print(await rec.gen_suggestions(some_name))

    await rec.tc.close()


if __name__ == "__main__":
    asyncio.run(main())
