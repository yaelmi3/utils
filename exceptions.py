import traceback
from contextlib import contextmanager

import log


@contextmanager
def document_exception(message="Exception occurred"):
    try:
        yield
    except:
        log.error(message)
        log.error(traceback.format_exc())


