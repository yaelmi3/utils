import traceback
from contextlib import contextmanager

from logs import log


@contextmanager
def document_exception():
    try:
        yield
    except:
        log.error(traceback.format_exc())


