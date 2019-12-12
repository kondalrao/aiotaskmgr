"""Logging."""
import json as pyjson
import asyncio
import eliot
import aiofiles
import logging
import logging.config
from logging import CRITICAL, DEBUG, ERROR, INFO, WARNING, Handler

from eliot import (add_destinations, add_global_fields, write_traceback)   # noqa
from eliot.json import EliotJSONEncoder
from pprint import pprint as print
from eliot.testing import capture_logging
# from eliot.stdlib import EliotHandler


class NXOSHandler(Handler):
    def emit(self, record):
        eliot.log_message(
            message_type="nxosdebug",
            log_level=record.levelname,
            # logger=record.name,
            message=record.getMessage(),
        )
        if record.exc_info:
            write_traceback(exc_info=record.exc_info)


class MyEncoder(EliotJSONEncoder):
    def default(self, obj):
        if hasattr(obj, '_to_json'):
            return obj._to_json()
        return EliotJSONEncoder.default(self, obj)


class AsyncFileDestination(object):

    def __init__(self, file, eliot_logging):
        self.eliot_logging = eliot_logging
        self.log_level = eliot_logging.log_level
        self._file = file
        self._logfile_task = asyncio.create_task(self.logfile_task(), name="logfile_task")
        self._logfile_task_q = self._logfile_task.context['tq']

    async def logfile_task(self):
        async with aiofiles.open(self._file, "w") as log_file:
            while True:
                (_, buff) = await self._logfile_task_q.get()
                while not self._logfile_task_q.empty():
                    (_, msg) = self._logfile_task_q.get_nowait()
                    buff = buff + msg

                await log_file.write(buff)

    # async def logfile_task(self):
    #     async with aiofiles.open(self._file, "w") as log_file:
    #         while True:
    #             (_, buff) = await self._logfile_task_q.get()
    #             await log_file.write(buff)


    def __call__(self, message):
        """
        @param message: A message dictionary.
        """
        def write_file(msg):
            self._file.write(pyjson.dumps(message, cls=MyEncoder) + '\n')
            self._file.flush()

        def write_file2(msg):
            data = f"{message['timestamp']:020} {message['logger']:25} {message['log_level']:10} {message['message']}"
            print(data)

        if(self.log_level <= logging.getLevelName(message['log_level'])):
            msg = pyjson.dumps(message, cls=MyEncoder) + '\n'
            self._logfile_task_q.put_nowait((0, msg))

        # if(self.log_level == logging.DEBUG):
        #     write_file2(message)


class Logging():
    log_level = logging.DEBUG
    root_logger = logging.getLogger()
    components = {'root': log_level,
                       'asyncio': log_level,
                       'aiomonitor': log_level,
                       'concurrent': log_level,
                       'aiotaskmgr': log_level,
                       'nxosdebug': log_level
                       }
    loglevel_mapping = {
        50: 'CRITICAL',
        40: 'ERROR',
        30: 'WARNING',
        20: 'INFO',
        10: 'DEBUG',
        0: 'NOTSET',
    }

    def nxos_stdout(self, message):
        if(self.log_level == logging.DEBUG):
            data = f"{message['timestamp']:020} {message['logger']:25} {message['log_level']:10} {message['message']}"
            print(data)


    def reset_logging(self, conf=None):
        """ Reset logging.

        Removes any configured handlers and filters.
        Sets new configuration (if provided).
        """
        list(map(self.root_logger.removeHandler, self.root_logger.handlers[:]))
        list(map(self.root_logger.removeFilter, self.root_logger.filters[:]))
        if conf is not None:
            logging.config.dictConfig(conf)

    def add_logging(self, comp: str, lvl: int = logging.ERROR):
        self.components[comp] = lvl

    def list_logging(self):
        return self.components

    def set_log_level_all(self, lvl: int):
        self.log_level = lvl

        for comp, lvl in self.components.items():
            logging.getLogger(comp).setLevel(lvl)

    def configure(self, lvl: int):
        self.log_level = lvl

        logging.basicConfig(level=self.log_level)
        # reset_logging()

        self.root_logger.setLevel(self.log_level)
        logger.setLevel(self.log_level)
        self.root_logger.addHandler(NXOSHandler())
        self.set_log_level_all(self.log_level)

        add_global_fields(message_type="aiotaskmgr")
        add_global_fields(log_level="INFO")

    def new_destination(self, file):
        add_destinations(AsyncFileDestination(file, self))
        # add_destinations(nxos_stdout)

        # to_file(sys.stdout)
        # to_file(open("nxosdebug.log", "w"))


eliot_logging = Logging()
logger = logging.getLogger('nxosdebug.internal')
