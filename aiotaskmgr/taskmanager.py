"""Task Manager Class."""

import asyncio
import logging
import signal
import uuid
from contextlib import suppress
from typing import Any, Dict, Callable, NoReturn
import aiotaskmgr
from aiotaskmgr.webmonitor import WebMonitor

from eliot import Action, start_task, start_action, log_call, current_action

if aiotaskmgr.use_uvloop:
    from uvloop import EventLoopPolicy as __BaseEventLoopPolicy
    from uvloop import Loop as __BaseLoop
else:
    from asyncio import DefaultEventLoopPolicy as __BaseEventLoopPolicy
    from asyncio import SelectorEventLoop as __BaseLoop


class Loop(__BaseLoop):
    """Loop.

    """

    def __init__(self):
        super().__init__()
        self.loop_id = uuid.uuid4()

    def _to_json(self):
        info = {}
        info['running'] = self.is_running()
        info['closed'] = self.is_closed()
        info['debug'] = self.is_running()

        return info

    def __repr__(self):
        return (
            f'<TaskManager.Loop running={self.is_running()} '
            f'closed={self.is_closed()} debug={self.get_debug()}>'
        )


class EventLoopPolicy(__BaseEventLoopPolicy):
    """EventLoopPolicy.

    """

    def _loop_factory(self) -> Loop:
        """

        Returns:
            Loop: TaskManager loop.
        """
        _loop = TaskManager().get_event_loop()
        if _loop is None:
            TaskManager().set_event_loop(Loop())
            _loop = TaskManager().get_event_loop()

        return _loop


def _update_source_traceback(task: asyncio.tasks.Task):
    """Reset the source_traceback for a given asyncio.tasks.Task

    Args:
        task (asyncio.tasks.Task): asyncio task

    Returns:

    """
    return

    # if task._source_traceback:  # noqa
    #         del task._source_traceback[-1]  # noqa


class AIOTaskMgrException(Exception):
    """Exception raised when an application reset is requested.

    """


class AIOTask(asyncio.Task):
    def __init__(self, coro, base_task, *, loop=None, name=None):
        super(AIOTask, self).__init__(coro, loop=loop, name=name)
        self.base_task = base_task

    def set_name(self, value):
        super(AIOTask, self).set_name(value)
        self.base_task.name = str(value)

    def _to_json(self):
        return super(AIOTask, self)._repr_info()



class BaseTask(object):
    """BaseTask for the all TaskManager Task classes.

    """


    def __init__(self, name):
        """BaseTask for the all TaskManager Task classes.

        Args:
            name (str): Name of the Task.
        """

        self.name = name
        self._task = None
        self._tm = TaskManager()
        self._loop = self._tm.get_event_loop()
        self._queue = asyncio.PriorityQueue()
        self._context = {'tq': self._queue, 'eliot_task': current_action().serialize_task_id()}
        self.logger = logging.getLogger('aiotaskmgr.TaskManager.Task')

    def __repr__(self):
        info = [f"{self.__class__.__name__}: {self.name}"]
        info.append(f"q_len: {self._queue.qsize()}")
        info.append(f"task: {self._task}")

        return '<{}>'.format(' '.join(info))

    def __str__(self):
        info = [f"{self.__class__.__name__}: {self.name}"]
        info.append(f"q_len: {self._queue.qsize()}")
        info.append(f"task: {self._task}")

        return '<{}>'.format(' '.join(info))

    def _to_json(self):
        info = {}
        info['name'] = self.name
        info['q_len'] = self._queue.qsize()
        info['task'] = self._task

        return info

    def get_task(self):
        """asyncio.tasks.Task: Get the asyncio.tasks.Task.

        """
        return self._task

    @property
    def name(self):
        """str: Get the name of the Task.

        """
        return self.__name

    @name.setter
    def name(self, name):
        """str: Get the name of the Task.

        """
        self.__name = str(uuid.uuid4()) if name is None else name

        return self.__name

    def set_log_level(self, lvl: int) -> NoReturn:
        """Set the log level for the Task.

        Args:
            lvl (int):
        """
        self.logger.setLevel(lvl)

    def _on_task_done(self, task):
        """Task callback.

        Args:
            task (asyncio.task.Task):
        """
        with Action.continue_task(task_id=self._context['eliot_task']):
            self.logger.debug(f"Task done: {self.name}")
            self._tm.unregister_task(self)

    def create_task(self):
        """Create a new asyncio.task.Task.

        Note:
            Must be called by the child classes.

        Returns:
            asyncio.task.Task: Task
        """
        _task = self._tm.create_task(self, self.name)
        self._context['eliot_task'] = current_action().serialize_task_id()
        return _task


class TaskManager(object):
    """Singleton TaskManager.

    """

    __instance: object = None

    # @log_call(include_args=[], include_result=False)
    def __new__(cls, loop=None) -> object:
        """New instance creation.

        Args:
            loop (Loop):
            uvloop (bool):
        """
        if TaskManager.__instance is None:
            logging.info('Creating a new instance of TaskManager.')
            TaskManager.__instance = object.__new__(cls)
            TaskManager.__instance._loop = loop
            TaskManager.__instance._tasks = {}
            TaskManager.__instance._interval = 1
            TaskManager.__instance.logger = logging.getLogger('aiotaskmgr.TaskManager')

            if loop is None:
                loop = TaskManager.__instance.__get_new_loop()
                TaskManager.__instance._loop = loop

            TaskManager.__instance.__setup_webmonitor()
        # else:
        #     TaskManager.__instance.logger.debug(f'TaskManager is already created. {TaskManager.__instance}')

        return TaskManager.__instance

    @classmethod
    # @log_call(include_args=[], include_result=False)
    def __get_new_loop(cls):
        """Get a new event loop and tie it with TaskManager.

        Returns:
            Loop: TaskManager's running loop
        """
        try:
            loop = asyncio.get_running_loop()
            print(loop)
            for task in loop.all_tasks():
                task.cancel()
            loop.close()
        except RuntimeError:
            pass

        asyncio.set_event_loop_policy(EventLoopPolicy())
        _loop = asyncio.new_event_loop()
        _loop.set_task_factory(TaskManager.__task_factory)
        _loop.set_debug(True)

        _loop.add_signal_handler(signal.SIGABRT, TaskManager.__handle_exit, signal.SIGQUIT)
        _loop.add_signal_handler(signal.SIGABRT, TaskManager.__handle_exit, signal.SIGTERM)
        _loop.add_signal_handler(signal.SIGABRT, TaskManager.__handle_exit, signal.SIGINT)
        _loop.add_signal_handler(signal.SIGABRT, TaskManager.__handle_exit, signal.SIGABRT)

        return _loop

    def __setup_webmonitor(self):
        """Setup Webmonitor.

        """
        TaskManager.__instance._aiom = WebMonitor(self._loop, TaskManager.__instance)
        TaskManager.__instance._aiom.start()

    @staticmethod
    def __handle_exit(sig: int) -> None:
        """

        Args:
            sig ():
        """
        logging.critical(f"Received {signal.strsignal(sig)}")
        raise AIOTaskMgrException(f"Application reset requested via {signal.strsignal(sig)}")

    def _to_json(self):
        """

        Returns:

        """

        info = {}

        if hasattr(self, '_tasks'):
            info['tasks'] = len(self._tasks)

        if hasattr(self, '_loop'):
            info['loop'] = self._loop

        return info

    def __repr__(self):
        """

        Returns:

        """
        num_tasks = len(self._tasks)
        return f"Taskmanager: {num_tasks=}"

    def __str__(self):
        """

        Returns:

        """
        num_tasks = len(self._tasks)
        return f"Taskmanager: {num_tasks=}"

    @staticmethod
    # @log_call(action_type="__task_factory", include_args=['_loop'], include_result=False)
    def __task_factory(_loop, coro):
        """

        Args:
            loop (Loop):
            coro ():

        Returns:
            asyncio.tasks.Task: Task
        """

        # TODO: Sanity check for _loop to be same sa Taskmanager._loop
        with start_task(action_type="TaskFactory", loop=_loop):
            task = Task(coro, name=None).get_task()
            _update_source_traceback(task)

        return task

    @log_call(action_type="__create_task", include_args=['task'], include_result=False)
    def __create_task(self, task):
        """

        Args:
            task (Task):

        Returns:
            asyncio.tasks.Task: Task
        """
        # self.logger.debug(f"fn: __create_task: {task}")
        # task._task = asyncio.tasks.Task(task._coro, loop=self._loop, name=task.name)
        task._task = AIOTask(task._coro, task, loop=self._loop, name=task.name)

        task._task.Task = task
        task._task.add_done_callback(task._on_task_done)

        _update_source_traceback(task._task)

        try:
            task._task.context = {}
            task._task.context = asyncio.current_task(loop=self._loop).context
        except AttributeError:
            pass
        finally:
            task._task.context.update(task._context)

        self.logger.debug(f"created asyncio task: {task._task.get_name()}")
        self.register_task(task)

        return task._task

    @log_call(action_type="create_task", include_args=['task_or_coro'], include_result=False)
    def create_task(self, task_or_coro, name):
        """Create a Task.

        If the task_or_coro is of type BaseTask go ahead and create asyncio task.
        If the task_or_coro is of type coroutine, then create a Task which will
        call this function again.

        Args:
            task_or_coro ():
            name (str):

        Returns:
            asyncio.tasks.Task: Task object.
        """

        if isinstance(task_or_coro, Task):
            task = self.__create_task(task_or_coro)
        else:
            task = Task(task_or_coro, name).get_task()

        return task

    def get_event_loop(self):
        """Get event loop.

        Returns:
            Loop: loop

        """
        return self._loop

    def set_event_loop(self, loop) -> NoReturn:
        """Set event loop

        Args:
            loop (Loop):
        """

        self._loop = loop

    def new_event_loop(self) -> Loop:
        """Get new event loop.

        Note:
            The current running event loop will be closed.

        Returns:
            Loop: event loop.

        """
        # TODO: Update Webmonitor with the new loop.
        self.close_event_loop()
        self._loop = self.__get_new_loop()

        self.logger.info(f"Created new event loop {self._loop}")

        return self.get_event_loop()

    def close_event_loop(self) -> NoReturn:
        """Close the current running event loop.

        """

        self.logger.info(f"Closing event loop {self._loop}")
        self.cancel_tasks()

        if self._loop is not None:
            self._loop.close()

        self._loop = None

    def set_log_level(self, lvl: int) -> NoReturn:
        """Set logging level.

        Args:
            lvl (int): Logging level
        """
        self.logger.setLevel(lvl)  # noqa

    async def _tick(self) -> NoReturn:
        """Start a periodic 1 sec tick.

        """
        task = asyncio.current_task(self._loop)
        self.logger.debug(f"Running {task.name}")

    def start_tick(self) -> NoReturn:
        """Start a periodic 1 sec tick.

        """
        PeriodicTask(1, self._tick, name='timer')

    def get_tasks(self) -> Dict:
        """Return all tasks.

        Returns:
            Dict
        """
        return self._tasks

    def get_task(self, atask: asyncio.Task) -> Any:
        """Return Task based on atask key.

        Args:
            atask ():

        Returns:

        """
        if atask in self._tasks:
            return self._tasks[atask]
        else:
            raise KeyError(f"Cannot find task {atask}.")

    def register_task(self, task: BaseTask) -> NoReturn:
        """Register the task to the TaskManager.

        Args:
            task (BaseTask):
        """

        self._tasks[task._task] = task
        self.logger.info(f"Registered task: {task.name}")

    def unregister_task(self, task) -> NoReturn:
        """Unregister the task from the TaskManager.

        Args:
            task (BaseTask):
        """

        self._tasks.pop(task.get_task())
        self.logger.info(f"Unregistered task: {task.name}")

    def cancel_tasks(self) -> NoReturn:
        """Cancel all the running tasks.

        """

        self.logger.debug(f"Canceling all tasks.")
        try:
            loop = asyncio.get_running_loop()
            for task in loop.all_tasks():
                task.cancel()
            loop.close()
        except RuntimeError:
            pass

    @log_call(action_type="set_context_key")
    def set_context_key(self, key: Any, value: Any) -> NoReturn:
        """Sets the key in the task.context dict and Task._context dict."""
        ctask = asyncio.current_task(loop=self._loop)
        task = self._tasks.get(ctask)

        task._context[key] = value
        ctask.context[key] = value

    @log_call(action_type="get_context_key")
    def get_context_key(self, key: Any, default: Any = None) -> Any:
        """Retrieves the value for the key from task.context"""
        ctask = asyncio.current_task(loop=self._loop)
        return ctask.context.get(key, default)

    @log_call(action_type="set_context")
    def set_context(self, ctx: Dict) -> NoReturn:
        """Sets the key in the task.context dict and Task._context dict."""
        ctask = asyncio.current_task(loop=self._loop)
        task = self._tasks.get(ctask)

        task._context = ctx
        ctask.context = ctx

    @log_call(action_type="update_context")
    def update_context(self, ctx: Dict) -> NoReturn:
        """Sets the key in the task.context dict and Task._context dict."""
        ctask = asyncio.current_task(loop=self._loop)
        task = self._tasks.get(ctask)

        task._context.update(ctx)
        ctask.context.update(ctx)

    @log_call(action_type="get_context")
    def get_context(self) -> Dict:
        """Retrieves the value for the key from task.context"""
        ctask = asyncio.current_task(loop=self._loop)
        return ctask.context

    async def join(self):
        """Task join."""
        self.logger.debug("Gathering all tasks.")
        await asyncio.gather(*self._tasks)

    async def __aenter__(self):
        """Context Enter."""
        self.logger.debug("__aenter__")
        return self

    async def __aexit__(self, exc_type, exc, t_b):
        """Context Exit."""
        self.logger.debug("__aexit__")
        return self

    def __enter__(self):
        """Context Enter."""
        self.logger.debug("__enter__")
        return self

    def __exit__(self, exc_type, exc, t_b):
        """Context Exit."""
        self.logger.debug("__exit__")
        with suppress(KeyboardInterrupt):
            self._loop.run_forever()
        return asyncio.gather(*self._tasks.keys())


class Task(BaseTask):
    """docstring for Task."""

    @log_call(action_type="Task", include_args=['name'], include_result=False)
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

        self.create_task()
        _update_source_traceback(self._task)

        # print(', '.join("%s: %s" % item for item in vars(self).items()))
        # print(self._task)


class PeriodicTask(BaseTask):
    """docstring for PeriodicTask."""

    def __init__(self, interval: int, coro: Callable, name, *args, **kwargs):
        """PeriodicTask.__init__."""
        super(Task, self).__init__(name)

        self._iter = 0
        self._interval = interval
        self._coro = coro
        self._args = args
        self._kwargs = kwargs
        self._timer_task = self._loop.call_soon_threadsafe(self.__run)

    def __run(self):
        self._timer_task = self._tm.create_task(self._run(), f"periodic_task: {self.name}")

    async def _run(self):
        self.logger.debug(f"PeriodicTask:{self.name} run timer interval {self._interval}...")
        while self._interval:
            with start_action(action_type=f"PeriodicTask:create_task:{self.name}-{self._iter}"):
                self._tm.create_task(self._coro(*self._args, **self._kwargs), name=f"{self.name}-{self._iter}")
                await asyncio.sleep(self._interval)
                self._iter += 1


class DelayedTask(BaseTask):
    """docstring for DelayedTask."""

    def __init__(self, delay: int, coro, name):
        """DelayedTask.__init__."""
        super(Task, self).__init__(name)

        self._delay = delay
        self._coro = coro
        self._timer_task = self._loop.call_later(self._delay, self._run)

    def _run(self):
        self._task = self._tm.create_task(self._coro, name=self.name)


# Initialize by default
# tm = TaskManager(None)
# tm.get_event_loop().set_debug(True)
