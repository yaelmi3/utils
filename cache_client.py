import pickle
import rpyc


def connect_to_cache():
    return rpyc.connect("yaelm-freddy", 6378)


def update_cache(key_name, data, days_to_keep=30):
    """
    1. Serialize given object
    2. Send object to cache server
    3. Raise exception if couldn't add to cache
    :type key_name: str
    :type data: object
    """
    pickled_object = pickle.dumps(data)
    connection = connect_to_cache()
    connection.root.exposed_add_to_cache(key_name, pickled_object, days_to_keep)


def get_from_cache(key_name):
    connection = connect_to_cache()
    pickled_object = connection.root.exposed_get_from_cache(key_name)
    if pickled_object:
        return pickle.loads(pickled_object)

