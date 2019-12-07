"""Task Manager Class."""

import asyncio
import logging
import signal
from contextlib import suppress
from uvloop import Loop as __BaseLoop
from uvloop import EventLoopPolicy as __BaseEventLoopPolicy
from typing import Any, Dict, Awaitable, Callable, Generator, Union, NoReturn

from aiotaskmgr.logging import start_action

from .webmonitor import WebMonitor


class AIOTaskMgrException(Exception):
    """Exception raised when an application reset is requested."""


class Loop(__BaseLoop):
    pass


class EventLoopPolicy(__BaseEventLoopPolicy):
    def _loop_factory(self):
        loop = TaskManager().get_event_loop()
        return Loop() if loop is None else loop


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


class TaskManager(object):
    """Singleton TaskManager."""

    __instance = None

    def __new__(cls, loop=None):
        """Control instance creation."""
        if TaskManager.__instance is None:  # pragma: no branch
            TaskManager.__instance = object.__new__(cls)
            TaskManager.__instance._loop = Loop() if loop is None else loop
            TaskManager.__instance._tasks = {}
            TaskManager.__instance._interval = 1
            TaskManager.__instance.logger = logging.getLogger('aiotaskmgr.TaskManager')
            TaskManager.__instance.__setup_taskmanager()
        return TaskManager.__instance

    def __setup_taskmanager(self):
        if self._loop is not None:   # pragma: no branch
            asyncio.set_event_loop_policy(EventLoopPolicy())
            self._loop = asyncio.get_event_loop()
            self._loop.set_debug(True)
            self._loop.add_signal_handler(signal.SIGABRT, TaskManager.__handle_exit, signal.SIGQUIT)
            self._loop.add_signal_handler(signal.SIGABRT, TaskManager.__handle_exit, signal.SIGTERM)
            self._loop.add_signal_handler(signal.SIGABRT, TaskManager.__handle_exit, signal.SIGINT)
            self._loop.add_signal_handler(signal.SIGABRT, TaskManager.__handle_exit, signal.SIGABRT)

        self._loop.set_task_factory(TaskManager.__task_factory)
        TaskManager.__instance._aiom = WebMonitor(loop=self._loop)
        TaskManager.__instance._aiom.start()

    @staticmethod
    def __handle_exit(sig: int) -> None:
        logging.critical(f"Received {signal.strsignal(sig)}")
        raise AIOTaskMgrException(f"Application reset requested via {signal.strsignal(sig)}")

    @staticmethod
    def __task_factory(loop, coro):
        """Create a Task."""
        task = Task(coro, name=None).get_task()

        if task._source_traceback:  # noqa
            del task._source_traceback[-1]  # noqa

        return task

    def __repr__(self):
        """__repr__."""
        num_tasks = len(self._tasks)
        return f"Taskmanager: {num_tasks=}"

    def __str__(self):
        """__repr__."""
        num_tasks = len(self._tasks)
        return f"Taskmanager: {num_tasks=}"

    def get_event_loop(self):
        return self._loop

    def set_event_loop(self, loop) -> NoReturn:
        self._loop = loop  # noqa
        self.__setup_taskmanager()

    def new_event_loop(self) -> NoReturn:
        # TODO: Update Webmonitor with the new loop.
        self.cancel_tasks()
        self._loop.close()
        self._loop = None
        self.__setup_taskmanager()

    def close_event_loop(self) -> NoReturn:
        self.cancel_tasks()
        self._loop.close()
        self._loop = None

    def set_log_level(self, lvl: int) -> NoReturn:
        self.logger.setLevel(lvl)  # noqa

    async def tick(self):
        task = asyncio.current_task(self._loop)
        self.logger.debug(f"Running {task.get_name()}")

    def start_tick(self) -> NoReturn:
        PeriodicTask(1, self.tick, name='timer')

    def _on_task_done(self, task) -> NoReturn:
        self.logger.debug(f"Task done: {task.get_name()}")
        self._tasks.pop(task)

    def get_tasks(self) -> Dict:
        """get_tasks: Return all tasks."""
        return self._tasks

    def get_task(self, atask: asyncio.Task) -> Any:
        """get_task: return Task based on atask key."""
        if atask in self._tasks:
            return self._tasks[atask]
        else:
            raise KeyError(f"Cannot find task {atask}.")

    def register_task(self, atask, task: BaseTask) -> NoReturn:
        """Register Task."""
        self._tasks[atask] = task
        self.logger.info(f"Registering task: {atask.get_name()}")

    def cancel_tasks(self) -> NoReturn:
        for task in asyncio.Task.all_tasks():
            task.cancel()

    def set_context_key(self, key: Any, value: Any) -> NoReturn:
        """Sets the key in the task.context dict and Task._context dict."""
        ctask = asyncio.current_task(loop=self._loop)
        task = self._tasks.get(ctask)

        task._context[key] = value
        ctask.context[key] = value

    def get_context_key(self, key: Any, default: Any =None) -> Any:
        """Retrieves the value for the key from task.context"""
        ctask = asyncio.current_task(loop=self._loop)
        return ctask.context.get(key, default)

    def set_context(self, ctx: Dict) -> NoReturn:
        """Sets the key in the task.context dict and Task._context dict."""
        ctask = asyncio.current_task(loop=self._loop)
        task = self._tasks.get(ctask)

        task._context = ctx
        ctask.context = ctx

    def update_context(self, ctx: Dict) -> NoReturn:
        """Sets the key in the task.context dict and Task._context dict."""
        ctask = asyncio.current_task(loop=self._loop)
        task = self._tasks.get(ctask)

        task._context.update(ctx)
        ctask.context.update(ctx)

    def get_context(self) -> Dict:
        """Retrieves the value for the key from task.context"""
        ctask = asyncio.current_task(loop=self._loop)
        return ctask.context

    def create_task(self, task: BaseTask) -> Any:
        """Create an asyncio task"""
        atask = asyncio.tasks.Task(task._coro, loop=self._loop, name=task._name)
        atask.add_done_callback(self._on_task_done)

        if atask._source_traceback:
            del atask._source_traceback[-1]

        try:
            atask.context = {}
            atask.context = asyncio.current_task(loop=self._loop).context
        except AttributeError:
            pass
        finally:
            atask.context.update(task._context)

        self.register_task(atask, task)

        return atask

    async def join(self):
        """Task join."""
        await asyncio.gather(*self._tasks)

    async def __aenter__(self):
        """Context Enter."""
        return self

    def __aexit__(self, exc_type, exc, t_b):
        """Context Exit."""
        return self.join()

    def __enter__(self):
        """Context Enter."""
        return self

    def __exit__(self, exc_type, exc, t_b):
        """Context Exit."""
        with suppress(KeyboardInterrupt):
            self._loop.run_forever()
        return asyncio.gather(*self._tasks.keys())


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
        # print(', '.join("%s: %s" % item for item in vars(self).items()))
        print(self)

    def __repr__(self):
        return f"Task: {self._task.get_name()} q_len: {self._queue.qsize()}"



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
