import os
import sys
import time
from contextlib import contextmanager
from pathlib import Path
from logbook import Logger, StreamHandler, FileHandler, NullHandler
import config

TEST_DIRECTORY_FORMAT = 'automation_iu-{date}-{time}-{pid}'
log_format_string = ("{record.time:%Y-%m-%d %H:%M:%S} {record.process} {record.module}:{record.func_name}:{record.lineno} {record.level_name}> {record.message}")
log = Logger('Logbook')
debug = log.debug
info = log.info
notice = log.notice
warning = log.warning
error = log.error
critical = log.critical
exception = log.exception


@contextmanager
def silence_log_output():
    NullHandler().push_application()
    yield
    StreamHandler(sys.stdout, level="INFO").push_application()


def init_log(log_file=True, file_path=None):
    if log_file:
        file_path = os.path.join(_get_logs_dir(), config.log_name) if not file_path else file_path
        log_file_handler = FileHandler(file_path, format_string=log_format_string, bubble=True, mode='a')
        log_file_handler.format_string = log_format_string
        print(f"Session logs can be found here {file_path}")
        log_file_handler.push_application()
        log.handlers.append(log_file_handler)
    log.handlers.append(StreamHandler(sys.stdout, level="DEBUG", format_string=log_format_string))


def _get_logs_dir():
    logs_dir = os.path.join(str(Path.home()),
                            'automation_ui',
                            TEST_DIRECTORY_FORMAT.format(
                                date=time.strftime("%d.%m.%Y"),
                                time=time.strftime("%H-%M-%S"),
                                pid=os.getpid()))
    if not os.path.isdir(logs_dir):
        os.makedirs(logs_dir)
    return logs_dir
