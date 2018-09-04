import arrow
import requests
from backslash import Backslash
from urlobject import URLObject

import config
import log
from cache_client import get_from_cache, add_to_cache



def get_session_tests(session):
    """
    1. Check if cache contain the list of session tests
    2. If found in cache, return tests
    3. If not found in cache, query tests from session and convert them to objects
    4. update session with tests in cache, to be kept for 2 days
    5. update tests separately in cache as well
    :type session: backslash.session.Session
    :rtype: list(backslash.test.Test)
    """
    session_key = f"session_{session.id}"
    log.info(f"Looking for session {session.id} in cache")
    tests = get_from_cache(session_key)
    if tests:
        log.info(f"Found session {session.id} in cache")
    else:
        log.info(f"Session {session.id} wasn't found in cache")
        tests = [test for test in session.query_tests()]
        add_to_cache(session_key, tests, ttl=2)
        for test in tests:
            add_to_cache(test.id, test)
    return tests


def get_latest_sessions(days_shift, show_successful=False):
    """
    1. Generate timestamp to be used in the query and add it to the query
    2. Execute query and in case result is ok, get the sessions from json
    3. While the query uses timestamp, some of the sessions are still older, so we filter them out
    :type days_shift: int
    :type show_successful: bool
    :rtype: list(backslash.session.Session)
    """
    timestamp = arrow.utcnow().shift(days=-days_shift).timestamp
    query = config.session_query_template.format(timestamp, str(show_successful).lower())
    log.info(f"Executing query {query}")
    result = requests.get(query)
    if result.ok:
        return [locate_session(session["id"]) for session in result.json().get("sessions") if
                session['start_time'] > timestamp and session['status'] not in ["SUCCESS"]]


def locate_session(session_id):
    """
    Given a single session id, perform query on the backslash, and return the first (and the only)
    object in the list
    :type session_id: int
    :type: backslash.session.Session
    """
    return get_backslash_client().query_sessions().filter(id=session_id)[0]


def locate_test(test_id):
    """
    Query tests by given test id and return the first (and the only) object
    :type test_id: int
    :rtype: backslash.test.Test
    """
    return get_backslash_client().query_tests().filter(id=test_id)[0]


def get_backslash_client():
    """
    Init and return backslash client instance
    :rtype: backslash.client.Backslash
    """
    server_address = URLObject(config.backslash_url)
    return Backslash(server_address, runtoken="")