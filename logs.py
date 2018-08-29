import sys
from logbook import NullHandler, StreamHandler
from contextlib import contextmanager

from logbook import Logger, StreamHandler

StreamHandler(sys.stdout).push_application()
log = Logger(__name__)


@contextmanager
def silence_log_output():
    NullHandler().push_application()
    yield
    StreamHandler(sys.stdout).push_application()