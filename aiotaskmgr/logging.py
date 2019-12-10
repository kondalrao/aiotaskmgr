"""Logging."""
import json as pyjson
import eliot
import logging
import logging.config
from logging import CRITICAL, DEBUG, ERROR, INFO, WARNING, Handler

from eliot import (add_destinations, add_global_fields,
                   to_file, write_traceback)   # noqa
from eliot.json import EliotJSONEncoder
from eliot.testing import capture_logging
# from eliot.stdlib import EliotHandler


log_level = logging.DEBUG
root_logger = logging.getLogger()
logger = logging.getLogger('nxosdebug.internal')


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

    def __init__(self, file):
        self._file = file

    def __call__(self, message):
        """
        @param message: A message dictionary.
        """
        def write_file(msg):
            self._file.write(pyjson.dumps(message, cls=MyEncoder) + '\n')
            # self._file.write(pyjson.dumps(message, cls=EliotJSONEncoder) + '\n')
            self._file.flush()

        def write_file2(msg):
            data = f"{message['timestamp']:020} {message['logger']:25} {message['log_level']:10} {message['message']}"
            print(data)

        if(log_level <= logging.getLevelName(message['log_level'])):
            write_file(message)

        # if(log_level == logging.DEBUG):
        #     write_file2(message)


def nxos_stdout(message):
    if(log_level == logging.DEBUG):
        data = f"{message['timestamp']:020} {message['logger']:25} {message['log_level']:10} {message['message']}"
        print(data)


def reset_logging(conf=None):
    """ Reset logging.

    Removes any configured handlers and filters.
    Sets new configuration (if provided).
    """
    root = logging.getLogger()
    list(map(root.removeHandler, root.handlers[:]))
    list(map(root.removeFilter, root.filters[:]))
    if not (conf is None):
        logging.config.dictConfig(conf)


def set_log_level(lvl: int):
    global log_level
    log_level = lvl

    logging.basicConfig(level=log_level)
    # reset_logging()

    root_logger.setLevel(log_level)
    root_logger.addHandler(NXOSHandler())

    logging.getLogger('asyncio').setLevel(log_level)
    logging.getLogger('aiomonitor').setLevel(log_level)
    logging.getLogger('concurrent').setLevel(log_level)
    logging.getLogger('aiotaskmgr').setLevel(log_level)

    logger.setLevel(log_level)

    add_global_fields(message_type="aiotaskmgr")
    add_global_fields(log_level="INFO")

    add_destinations(AsyncFileDestination(open('aiotaskmgr.log', "w")))
    # add_destinations(nxos_stdout)

    # to_file(sys.stdout)
    # to_file(open("nxosdebug.log", "w"))


set_log_level(log_level)
