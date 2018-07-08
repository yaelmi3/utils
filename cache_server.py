import sys

import baker
import redis
import rpyc
import timedelta
from logbook import Logger, StreamHandler
from rpyc.utils.server import ThreadedServer

REDIS_PORT = 6378
log = Logger(__name__)


class CacheServer(rpyc.Service):
    def __init__(self, *args):
        self.r_server = redis.Redis()

    def on_connect(self):
        log.info("Remote connect accepted")

    def exposed_add_to_cache(self, key_name, data, days_to_keep=30, overwrite=True):
        """
        If overwrite data is enabled, add the key to cache
        if overwrite data is False, check whether the key
        :type key_name: str
        :type data:
        :type days_to_keep: int
        :type overwrite: bool
        """
        log.info(
            f"Saving data ומגקר {key_name} with ttl={days_to_keep} days and overwrite={overwrite}")
        if not overwrite and self.r_server.exists(key_name):
            log.info(f"Key {key_name} already exists, no action is required")
        else:
            self.r_server.sadd(key_name, data)
            log.info(f"Key {key_name} was added to the cache")
        if days_to_keep:
            log.info(f"Updating days to keep data for {key_name} to {days_to_keep} days")
            self.r_server.expire(key_name, timedelta(days=days_to_keep))


if __name__ == "__main__":
    StreamHandler(sys.stdout).push_application()
    baker.run()
    log.info(f"Starting Lab cache server on port {REDIS_PORT}")
    t = ThreadedServer(CacheServer, port=REDIS_PORT)
    t.daemon = True
    t.start()
