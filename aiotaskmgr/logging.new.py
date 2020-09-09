"""Logging."""
import json as pyjson
import eliot
import logging
import logging.config
from logging import CRITICAL, DEBUG, ERROR, INFO, WARNING, Handler

from eliot import (add_destinations, add_global_fields,
                   to_file, write_traceback)   # noqa
from eliot.json import EliotJSONEncoder


class NXOSHandler(Handler):
    def emit(self, record):
        eliot.log_message(
            message_type="nxosdebug",
            log_level=record.levelname,
            logger=record.name,
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
        self._file = file

    def __call__(self, message):
        """
        @param message: A message dictionary.
        """
        msg_lvl = message['log_level']
        msg_comp = message['logger']
        print(message)

        def write_file(msg):
            self._file.write(pyjson.dumps(message, cls=MyEncoder) + '\n')
            self._file.flush()

        def write_file2(msg):
            if 'message' in message:
                data = f"{message['timestamp']:020} {message['logger']:25} {message['log_level']:10} {message['message']}"
                print(data)

        # if self.eliot_logging.components[msg_comp] >= msg_lvl:
            write_file(message)

        # if self.eliot_logging.log_level == logging.DEBUG or message['log_level'] > logging.WARN:
        #     write_file2(message)


class Logging(object):

    def __init__(self, lvl: int = logging.INFO):
        self.log_level = lvl
        self.root_logger = logging.getLogger()
        self.logger = logging.getLogger('nxosdebug.internal')
        self.components = {'root': self.log_level,
                           'asyncio': self.log_level,
                           'aiomonitor': self.log_level,
                           'concurrent': self.log_level,
                           'aiotaskmgr': self.log_level,
                           'nxosdebug': self.log_level
                           }
        self.loglevel_mapping = {
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

    def set_log_level_all(self, lvl: int):
        self.log_level = lvl

        # self.root_logger.setLevel(lvl)
        for comp, lvl in self.components.items():
            logging.getLogger(comp).setLevel(lvl)

    def configure(self, lvl: int):
        self.log_level = lvl
        self.set_log_level_all(lvl)

        logging.basicConfig(level=self.log_level)
        # self.reset_logging()

        self.root_logger.setLevel(self.log_level)
        self.root_logger.addHandler(NXOSHandler())

        for comp, lvl in self.components.items():
            if comp != 'root':
                logging.getLogger(comp).setLevel(lvl)

        # add_global_fields(message_type="aiotaskmgr")
        # add_global_fields(log_level='INFO')

        # add_destinations(nxos_stdout)

        # to_file(sys.stdout)
        # to_file(open("nxosdebug.log", "w"))

    def add_logging(self, comp: str, lvl: int = logging.ERROR):
        self.components[comp] = lvl

    def list_logging(self):
        return self.components

    def add_destination(self, file: str = 'aiotaskmgr.log'):
        """Add a destination.
        Note: add_destinatio has to be called after configure.

        Args:
            file ():

        Returns:

        """
        add_destinations(AsyncFileDestination(open(file, "w"), self))


eliot_logging = Logging()
logger = eliot_logging.logger
