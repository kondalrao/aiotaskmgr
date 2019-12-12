"""WebMonitor."""

import asyncio
from typing import NoReturn

import aiomonitor
from terminaltables import AsciiTable
from pprint import pprint as print


class WebMonitor(aiomonitor.Monitor):
    """Webmonitor."""

    def __init__(self, _loop, tm):
        super(WebMonitor, self).__init__(loop=_loop)
        self._tm = tm

    def do_hello(self, _sin, _sout, _name=None):
        """do_hello."""
        print("do_hello")

    def do_ps(self) -> NoReturn:
        """Show task table"""
        headers = ('Task ID', 'State', 'Task')
        table_data = [headers]
        tasks = asyncio.all_tasks(loop=self._loop)
        curr_task = asyncio.current_task(loop=self._loop)
        if curr_task is not None:
            self._sout.write(f"Current Task: taskid:{str(id(curr_task))}, Task:{curr_task.get_name()}\n")
            # self._sout.write(f"Current Task: taskid:{str(id(curr_task))}")

        for task in sorted(tasks, key=id):
            taskid = str(id(task))
            if task:
                table_data.append((taskid, task._state, task.get_name()))
        table = AsciiTable(table_data)
        self._sout.write(table.table)
        self._sout.write('\n')
        self._sout.flush()
