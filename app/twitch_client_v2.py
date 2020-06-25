import asyncio
from app.settings import TWITCH_CLIENT_ID, TWITCH_CLIENT_SECRET
from twitchio.client import Client
from time import perf_counter
from typing import Union


class TC(Client):
    
    def __init__(self):
        super().__init__(client_id=TWITCH_CLIENT_ID, client_secret=TWITCH_CLIENT_SECRET)
        self.http = self.http

    async def close(self):
        await self.http._session.close()

    async def get_fols(self, user_id, limit=None):
        params = [('to_id', user_id)]
        return await self.http.request('GET', '/users/follows', params=params, limit=limit, count=False)

    async def get_users(self, *users: Union[str, int]):
        users = await self.http.get_users(*users)
        return await users

    async def get_uids(self, *usr_name: tuple):
        uids = await self.http.get_users(*usr_name)
        return [int(user['id']) for user in uids]


async def main():
    tc = TC()
    test_names = ['stroopc', 'jitterted', 'strager']
    uids = await tc.get_uids(*test_names)
    print(uids)

    await tc.close()


if __name__ == "__main__":
    asyncio.run(main())

