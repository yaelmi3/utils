import sys
import rpyc
import baker
import redis
from rpyc.utils.server import ThreadedServer
from logbook import Logger, StreamHandler

REDIS_PORT = 6378
log = Logger(__name__)


class CacheServer(rpyc.Service):
    def __init__(self, *args):
        self.r_server = redis.Redis()

    def on_connect(self):
        log.info(f'{self}')


if __name__ == "__main__":
    if __name__ == '__main__':
        StreamHandler(sys.stdout).push_application()
        baker.run()
        log.info(f"Starting Lab cache server on port {REDIS_PORT}")
        t = ThreadedServer(CacheServer, port=REDIS_PORT)
        t.daemon = True
        t.start()
