# twitchbot.py in app/

from app.settings import *
from twitchio.ext import commands

from time import perf_counter


class Bot(commands.Bot):

    def __init__(self):
        super().__init__(irc_token=TMI_TOKEN, client_id=TWITCH_CLIENT_ID, client_secret=TWITCH_CLIENT_SECRET,
                        nick=BOT_NICK, prefix=BOT_PREFIX, initial_channels=CHANNELS )

    # Events don't need decorators when subclassed
    async def event_ready(self):
        print(f'Ready | {self.nick}')
        start_time = perf_counter()
        result = await self.get_followers(106071345)
        print(f'length: {len(result)}, \nresult: {result}')
        print('Gather time: {}'.format(perf_counter() - start_time))

    async def event_message(self, message):
        print(message.content)
        await self.handle_commands(message)

    # Commands use a decorator...
    @commands.command(name='test')
    async def my_command(self, ctx):
        await ctx.send(f'Hello {ctx.author.name}!')


    async def foo(self):
        return await self.get_followers(106071345)



if __name__ == '__main__':
    bot = Bot()
    bot.run()
