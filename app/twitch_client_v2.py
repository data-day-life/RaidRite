import asyncio
from app.settings import TWITCH_CLIENT_ID, TWITCH_CLIENT_SECRET
from twitchio.client import Client
from collections import Counter
from time import perf_counter


class TC(Client):
    
    def __init__(self, loop=None):
        self.loop = loop or asyncio.get_event_loop()
        super().__init__(loop=self.loop, client_id=TWITCH_CLIENT_ID, client_secret=TWITCH_CLIENT_SECRET)
        self.http = self.http


    async def close(self):
        await self.http._session.close()


    async def _get_total(self, user_id, params=None, limit=None):
        if not params:
            params = [('to_id', user_id)]
        return await self.http.request('GET', '/users/follows', params=params, limit=limit, count=True)


    async def get_total_followers(self, user_id):
        params = [('to_id', user_id)]
        return await self._get_total(user_id, params)


    async def get_total_followings(self, user_id):
        params = [('from_id', user_id)]
        return await self._get_total(user_id, params)


    # async def get_users(self, *users: Union[str, int]):
    #     users = await self.http.get_users(*users)
    #     return await users


    # async def get_uids(self, *usr_name: tuple):
    #     uids = await self.http.get_users(*usr_name)
    #     return [user['id'] for user in uids]


    async def get_uids(self, *user_names: tuple):
        return [user.id for user in await self.get_users(*user_names)]

    # async def get_follower_count(self, user_id):


async def main():
    tc = TC()
    test_names = ['stroopc', 'jitterted', 'strager']
    test_names = ['stroopc']
    uids = await tc.get_uids(*test_names)
    print(uids)

    # Followers
    fols = await tc.get_followers(uids[0])
    print(f'Followers: \n {fols}')

    # Followings
    fols = await tc.get_following(uids[0])
    print(f'Followings: \n {fols}')

    # Chatters
    chatters = await tc.get_chatters(*test_names)
    print(f'Chatters: \n {chatters}')

    await tc.close()


if __name__ == "__main__":
    start_time = perf_counter()
    asyncio.run(main())
    print(f'Run time: {round(perf_counter() - start_time, 3)} sec')

