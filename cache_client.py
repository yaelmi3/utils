import pickle
import rpyc

import config


def connect_to_cache():
    return rpyc.connect(config.cache_server.url, config.cache_server.port)


def update_cache(key_name, data, days_to_keep=30):
    """
    1. Serialize given object
    2. Send object to cache server
    3. If days to keep = 0, keep forever
    :type key_name: str
    :type data: object
    :type days_to_keep: int
    """
    pickled_object = pickle.dumps(data)
    connection = connect_to_cache()
    connection.root.exposed_add_to_cache(key_name, pickled_object, days_to_keep)


def get_from_cache(key_name):
    """
    1. Connect to cache
    2. If cache returned an object, unpickle it and return
    :type key_name: str
    """
    connection = connect_to_cache()
    pickled_object = connection.root.exposed_get_from_cache(key_name)
    if pickled_object:
        return pickle.loads(pickled_object)

