import sys
from datetime import timedelta

import redis
import rpyc
from logbook import Logger, StreamHandler
from rpyc.utils.server import ThreadedServer

REDIS_PORT = 6378
log = Logger(__name__)


class CacheServer(rpyc.Service):
    def __init__(self, *args):
        self.r_server = redis.Redis()

    def on_connect(self, *_):
        log.info("Remote connection accepted")

    def exposed_add_to_cache(self, key_name, data, days_to_keep=None):
        """
        If overwrite data is enabled, add the key to cache
        if overwrite data is False, check whether the key
        :type key_name: str
        :type data: bytes
        :type days_to_keep: int
        :type overwrite: bool
        """
        if self.r_server.exists(key_name):
            log.info(f"Key {key_name} already exists, overwriting it with new value")
            self.r_server.delete(key_name)
            self.r_server.sadd(key_name, data)
        else:
            self.r_server.sadd(key_name, data)
            log.info(f"Key {key_name} was added to the cache")

        if days_to_keep:
            log.info(f"Updating days to keep data for {key_name} to {days_to_keep} days")
            self.r_server.expire(key_name, timedelta(days=days_to_keep))

    def exposed_get_from_cache(self, key_name):
        """
        1. Check if key is found in cache
        2. To return the bytes object and not the set that is return by the redis, convert the data
            to list and return its first member
        :type key_name: str
        :rtype: bytes
        """
        log.info(f"Looking for objects matching {key_name}")
        if self.r_server.exists(key_name):
            log.info(f'Matching entry to {key_name} was found')
            return list(self.r_server.smembers(key_name))[0]
        log.info(f"Could not find {key_name}")


if __name__ == "__main__":
    StreamHandler(sys.stdout).push_application()
    log.info(f"Starting Lab cache server on port {REDIS_PORT}")
    t = ThreadedServer(CacheServer, port=REDIS_PORT)
    t.daemon = True
    t.start()
