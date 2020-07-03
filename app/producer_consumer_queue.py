import asyncio


class ProdConsQueue:

    def __init__(self, items, n_prods: int = 10, n_cons: int = 10):
        self.n_prods = n_prods
        self.n_cons = n_cons
        self.queue = asyncio.Queue()

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
        producers = [asyncio.create_task(self.produce(items, queue)) for _ in range(n_prods)]
        consumers = [asyncio.create_task(self.consume(queue)) for _ in range(n_cons)]

        # Begin production pool
        await asyncio.gather(*producers)

        # Wait until consumers have processed/consumed ALL given items
        await queue.join()

        # Cancel all consumers since they are still awaiting additional items
        for c in consumers:
            c.cancel()