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


    async def produce(self, items, q: asyncio.Queue) -> None:
        # Get followings
        for _, produced_result in enumerate(items):
            # Produce an item

            # Slow I/O operation

            # Parse result of I/O operation

            # Place final result of I/O operation on queue
            await q.put(produced_result)


    async def consume(self, q: asyncio.Queue) -> None:
        while True:
            # Wait for produced items to appear in queue
            q_item = await q.get()

            # Process q_item()

            # More I/O operations

            # Notify queue that item has been consumed
            q.task_done()


    async def run_queue(self, items, n_prods: int = 10, n_cons: int = 10):
        # Create new Queue
        queue = asyncio.Queue()

        # Create producer and consumer pool and supply items
        producers = [asyncio.create_task(self.produce(items, queue)) for n in range(n_prods)]
        consumers = [asyncio.create_task(self.consume(queue)) for n in range(n_cons)]
        
        # Begin production pool
        await asyncio.gather(*producers)

        # Wait until consumers have processed/consumed ALL given items
        await queue.join()

        # Cancel all consumers since they are still awaiting additional items
        for c in consumers:
            c.cancel()
    

class ProdConsQueue:

    def __init__(self, n_prods: int = 10, n_cons: int = 10, items):
        self.n_prods = n_prods
        self.n_cons = n_cons
        self.queue = asyncio.Queue()
        self.items = items





async def main():
    rec = Recommender()
    some_name = 'stroopc'
    print(await rec.gen_suggestions(some_name))

    await rec.tc.close()


if __name__ == "__main__":
    asyncio.run(main())
