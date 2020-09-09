"""docstring."""
import sys

if sys.version_info < (3, 8):
    raise RuntimeError("Needs python version >= 3.8")

use_uvloop: bool = True

from .taskmanager import (
    TaskManager,
    Task,
    DelayedTask,
    PeriodicTask
)  # noqa

from .webmonitor import WebMonitor
from .logging import logger
