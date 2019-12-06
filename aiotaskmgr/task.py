
import asyncio
from aiotaskmgr.taskmanager import TaskManager
from aiotaskmgr.logging import logging, start_action
from typing import Any, Awaitable, Callable, Generator, Union


class BaseTask(object):
    """docstring for Task."""
    def __init__(self, name):
        """BaseTask.__init__."""
        self._name = name
        self._task = None
        self._tm = TaskManager()
        self._queue = asyncio.Queue()
        self._loop = self._tm.get_event_loop()
        self._context = {'tq': self._queue}
        self.logger = logging.getLogger('aiotaskmgr.TaskManager.Task')

    def get_task(self):
        return self._task

    def get_name(self):
        return self._task.get_name if self._task else "None"

    def set_log_level(self, lvl: int):
        self.logger.setLevel(lvl)  # noqa

    def create_task(self, coro: Union[Generator[Any, None, Any], Awaitable[Any]], name=None):
        self._tm.create_task(coro, name)


class Task(BaseTask):
    """docstring for Task."""

    def __init__(self, coro, name, *args, **kwargs):
        """Task.__init__."""
        super(Task, self).__init__(name)

        self._args = args
        self._kwargs = kwargs

        if asyncio.iscoroutine(coro):
            self._coro = coro
        elif callable(self._coro):
            self._coro = coro(*args, **kwargs)
        else:
            raise TypeError(f"a coroutine was expected, got {coro!r}")

        self._task = self._tm.create_task(self)

    def __repr__(self):
        return f"Task: {self._task.get_name()}"



class PeriodicTask(BaseTask):
    """docstring for PeriodicTask."""

    def __init__(self, interval: int, name, coro: Callable, *args, **kwargs):
        """PeriodicTask.__init__."""
        super(Task, self).__init__(name)

        self._iter = 0
        self._interval = interval
        self._coro = coro
        self._args = args
        self._kwargs = kwargs
        self._timer_task = self._loop.call_soon_threadsafe(self.__run)

    def __repr__(self):
        return f"PeriodicTask: {self.get_name()}"

    def __run(self):
        self._timer_task = self._tm.create_task(self._run(), f"periodic_task: {self._name}")

    async def _run(self):
        # self._timer_task = self._loop.call_later(self._interval, self._run)
        self.logger.debug(f"PeriodicTask:{self._name} run timer interval {self._interval}...")
        while self._interval:
            with start_action(action_type=f"PeriodicTask:create_task:{self._name}-{self._iter}"):
                self._tm.create_task(self._coro(*self._args, **self._kwargs), name=f"{self._name}-{self._iter}")
                await asyncio.sleep(self._interval)
                self._iter += 1


class DelayedTask(BaseTask):
    """docstring for DelayedTask."""

    def __init__(self, delay: int, coro, name=None):
        """DelayedTask.__init__."""
        super(Task, self).__init__(name)

        self._delay = delay
        self._coro = coro
        self._timer_task = self._loop.call_later(self._delay, self._run)

    def __repr__(self):
        return f"DelayedTask: {self.get_name()}"

    def _run(self):
        self._task = self._tm.create_task(self._coro, name=self._name)
