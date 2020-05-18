import asyncio
from twitchio import client

from app.auth import Auth
from app.settings import TWITCH_CLIENT_ID

async def main():
    twitch_client = client.Client(client_id=TWITCH_CLIENT_ID)
    print(await twitch_client.get_users("stroopc"))
    print('')
    twitch_client.http._session.close()


if __name__ == "__main__":
    asyncio.run(main())

