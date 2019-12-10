"""Testing TaskManager class."""

import aiotaskmgr
import asyncio
import unittest
from aiotaskmgr.logging import capture_logging
from pprint import pprint as print


class TaskManagerTests(unittest.TestCase):

    def setUp(self) -> None:
        self.tm = aiotaskmgr.TaskManager()
        asyncio.new_event_loop()

    def tearDown(self) -> None:
        pass

    @classmethod
    def setUpClass(cls) -> None:
        pass

    @classmethod
    def tearDownClass(cls) -> None:
        pass

    async def test_taskmanager(self):
        """test_taskmanager."""
        tm1 = aiotaskmgr.TaskManager()
        tm2 = aiotaskmgr.TaskManager()

        self.assertEqual(tm1, tm2, "Failed.")

    def test_event_loop(self):
        tm_loop = self.tm.get_event_loop()
        loop = asyncio.get_event_loop()

        self.assertIsInstance(tm_loop, aiotaskmgr.taskmanager.Loop)
        self.assertIsInstance(loop, aiotaskmgr.taskmanager.Loop)
        self.assertEqual(tm_loop, loop)
        self.assertEqual(tm_loop.loop_id, loop.loop_id)

    def test_new_event_loop(self):
        tm_loop = self.tm.get_event_loop()
        nloop = self.tm.new_event_loop()
        loop = self.tm.new_event_loop()
        aloop = asyncio.get_event_loop()

        self.assertIsInstance(loop, aiotaskmgr.taskmanager.Loop)
        self.assertIsInstance(tm_loop, aiotaskmgr.taskmanager.Loop)
        self.assertIsInstance(aloop, aiotaskmgr.taskmanager.Loop)
        self.assertNotEqual(tm_loop.loop_id, loop.loop_id)
        self.assertNotEqual(tm_loop.loop_id, nloop.loop_id)
        self.assertNotEqual(tm_loop.loop_id, aloop.loop_id)
        self.assertNotEqual(nloop.loop_id, loop.loop_id)
        self.assertNotEqual(nloop.loop_id, aloop.loop_id)
        self.assertEqual(loop.loop_id, aloop.loop_id)

    def test_close_event_loop(self):
        tm_loop = self.tm.get_event_loop()

        self.tm.close_event_loop()
        loop = self.tm.get_event_loop()

        self.assertIsNone(loop)

        # Fixing the loop for other test cases
        loop = asyncio.get_event_loop()
        new_tm_loop = self.tm.get_event_loop()

        self.assertIsInstance(tm_loop, aiotaskmgr.taskmanager.Loop)
        self.assertIsInstance(loop, aiotaskmgr.taskmanager.Loop)
        self.assertNotEqual(tm_loop.loop_id, new_tm_loop.loop_id)
        self.assertNotEqual(tm_loop.loop_id, loop.loop_id)
        self.assertEqual(new_tm_loop.loop_id, loop.loop_id)

    def test_create_task01(self):
        """test_create_task01"""
        async def coro():
            await asyncio.sleep(1)

        self.tm._loop.run_until_complete(coro())

    @capture_logging(None)
    def test_create_task02(self, logger):
        """test_create_task."""

        async def coro_task():
            await asyncio.sleep(2)
            return 10

        async def coro():
            task = asyncio.create_task(coro_task(), name="test_create_task")

            self.assertIsInstance(task, asyncio.Task)
            self.assertIsInstance(self.tm.get_task(task), aiotaskmgr.taskmanager.Task)
            self.assertGreater(len(self.tm.get_tasks()), 1)

            result = await task
            print(result)


        self.tm.get_event_loop().run_until_complete(coro())
        # asyncio.get_event_loop().run_until_complete(coro())
