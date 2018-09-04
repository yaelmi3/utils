import traceback
from contextlib import contextmanager

import log


@contextmanager
def document_exception():
    try:
        yield
    except:
        log.error(traceback.format_exc())


