"""docstring."""

import asyncio
import aiounittest
from aiotaskmgr import TaskManager, Task


class TaskManagerTests(aiounittest.AsyncTestCase):
    """TaskManagerTests."""

    def get_event_loop(self):
        self.my_loop = TaskManager().get_event_loop()
        return self.my_loop

    def change_event_loop(self):
        try:
            old_loop = asyncio.get_event_loop()
            if not old_loop.is_closed():
                old_loop.close()
        except RuntimeError:
            # no default event loop, ignore exception
            pass
        _loop = asyncio.new_event_loop()
        asyncio.set_event_loop(_loop)

        return _loop

    async def test_create_task(self):
        """test_create_task."""
        tm = TaskManager()

        async def coro():
            await asyncio.sleep(1)

        task = asyncio.create_task(coro(), name="test_create_task")

        self.assertIsInstance(task, asyncio.Task)
        self.assertIsInstance(tm.get_task(task), Task)
        self.assertGreater(len(tm.get_tasks()), 1)

        task.cancel()

    # async def test_asyncio_create_task(self):
    #     """test_asyncio_create_task."""
    #     async def coro():
    #         await asyncio.sleep(1)
    #
    #     loop = self.get_event_loop()
    #     task = loop.create_task(coro(), name="test_asyncio_create_task")
    #
    #     with self.assertRaises(KeyError):
    #         TaskManager().get_task(task)
    #
    #     task.cancel()
