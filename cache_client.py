import pickle
import rpyc


def connect_to_cache():
    return rpyc.connect("yaelm-freddy", 6378).root


def update_cache(key_name, object):
    """
    1. Serialize given object
    2. Send object to cache server
    3. Raise exception if couldn't add to cache
    :param key_name:
    """
    pickled_object = pickle.dumps(object)
    connection = connect_to_cache()
    connection.exposed_add_to_cache(key_name, object)