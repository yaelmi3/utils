import pickle
import sys
from datetime import timedelta

import baker
import redis
import rpyc
from logbook import Logger, StreamHandler
from rpyc.utils.server import ThreadedServer

REDIS_PORT = 6378
log = Logger(__name__)


class CacheServer(rpyc.Service):
    def __init__(self, *args):
        self.r_server = redis.Redis()

    def on_connect(self):
        log.info("Remote connection accepted")

    def exposed_add_to_cache(self, key_name, data, ttl=60 * 60 * 2):
        """
        If overwrite data is enabled, add the key to cache
        if overwrite data is False, check whether the key
        :type key_name: str
        :type data: bytes
        :type ttl: int
        :type overwrite: bool
        """
        if self.r_server.exists(key_name):
            log.info(f"Key {key_name} exists")
            self.r_server.expire(key_name, timedelta(seconds=ttl))
        else:
            self.r_server.sadd(key_name, data)
            log.info(f"Key {key_name} was added to the cache")

        if ttl:
            log.info(f"Updating days to keep data for {key_name} to {ttl} seconds")
            self.r_server.expire(key_name, timedelta(seconds=ttl))

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
    baker.run()
    log.info(f"Starting Lab cache server on port {REDIS_PORT}")
    t = ThreadedServer(CacheServer, port=REDIS_PORT)
    t.daemon = True
    t.start()
