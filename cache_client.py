import pickle
import rpyc

import config


def connect_to_cache():
    return rpyc.connect(config.cache_server.url, config.cache_server.port)


def add_to_cache(key_name, data, days_to_keep=30):
    """
    1. Serialize given object
    2. Send object to cache server
    3. If days to keep = 0, keep forever
    :type key_name: Union(str, int)
    :type data: object
    :type days_to_keep: int
    """
    pickled_object = pickle.dumps(data)
    connection = connect_to_cache()
    connection.root.exposed_add_to_cache(key_name, pickled_object, days_to_keep)


def update_cache(key_name, new_data):
    """
    1. Get data and check whether the specified key exists
    2. If exists:
        2.1 Check whether it's a list, and if not, covert it to list
        2.2 If new data is not in the list, add it to the list, otherwise return
    3. If doesn't exist:
        3.1 Convert data to list
    3. Update cache with updated entry
    :type key_name: Union(str, int)
    :type new_data: object
    """
    entry = get_from_cache(key_name)
    if entry:
        if not isinstance(entry, list):
            entry = list(entry)
        if new_data not in entry:
            entry.append(new_data)
        else:
            return
    else:
        entry = [new_data]
    add_to_cache(key_name, entry)


def get_from_cache(key_name):
    """
    1. Connect to cache
    2. If cache returned an object, unpickle it and return
    :type key_name: Union(str, int)
    """
    connection = connect_to_cache()
    pickled_object = connection.root.exposed_get_from_cache(key_name)
    if pickled_object:
        return pickle.loads(pickled_object)

