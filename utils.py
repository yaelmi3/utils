import os
import sys
import tempfile
from itertools import chain

import arrow
import baker
import requests
from backslash import Backslash
from logbook import Logger, StreamHandler
from urlobject import URLObject

import config
from cache_client import add_to_cache, get_from_cache, update_cache

StreamHandler(sys.stdout).push_application()
log = Logger(__name__)


class InternalTest(object):
    def __init__(self, backslash_test, exception_info=None):
        test_data = backslash_test._data
        self.test_link = f'<a href="{backslash_test.ui_url}">{backslash_test.logical_id}</a>'
        self.test_name = test_data['info']['name']
        self.parameters =test_data['parameters']
        self.error = _determine_test_error(exception_info, test_data)
        self.version = test_data['subjects'][0]['version']
        self.start_time = arrow.get(test_data['start_time']).format('DD-MM-YY HH:mm:ss')
        self.duration = arrow.get(test_data['duration']).format('HH:mm:ss')
        self.user_name = test_data['user_display_name']
        self.branch = test_data['scm_local_branch'] if test_data['scm_local_branch'] else ''
        self.comment = test_data["last_comment"]['comment'] if test_data['num_comments'] else ''


def _determine_test_error(exception_info, test_data):
    """
    1. If exception_info was provided and it's not None, get the exception type from the error
    2. If exception info was not provided, get the test first error
    :type exception_info: backslash.error.Error
    :type test_data: dict
    :rtype str
    """
    if exception_info:
        return exception_info._data['exception_type']
    return test_data['first_error'].get('exception_type') if test_data.get(
        'first_error') else ''


def get_backslash_client():
    """
    Init and return backslash client instance
    :rtype: backslash.client.Backslash
    """
    server_address = URLObject(config.backslash_url)
    return Backslash(server_address, runtoken="")


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


def query_tests_by_name(test_name, show_successful=False):
    """
    1. Update query with test name and whether to query for successful test appearances
    2. Execute query and, in case it ended successfully, obtain the list of tests from the json
    3. Return list of converted test objects
    :type test_name: str
    :type show_successful: bool
    :rtype: list(backslash.session.Session)
    """
    query = config.test_query_template.format(test_name, str(show_successful).lower())
    log.info(f"Executing query: {query}")
    result = requests.get(query)
    if result.ok:
        meta_tests = result.json().get("tests")
        log.info(f"{len(meta_tests)} tests were found. Converting them to test objects")
        return [get_test(meta_test["id"]) for meta_test in meta_tests]


def get_test(test_id):
    """
    1. Check if test is in cache
    2. If test was found in cache return it
    3. If test wasnt found in cache, get the test from backslash
    4. Add test to cache
    :type test_id: int
    :rtype: backslash.test.Test
    """
    log.info(f"Looking for test {test_id} in cache")
    cached_test = get_from_cache(test_id)
    if cached_test:
        log.info("Test was found in cache")
        return cached_test
    log.info(f"Could not find test {test_id} in cache, obtaining from backslash")
    backslash_test = locate_test(test_id)
    add_to_cache(test_id, backslash_test)
    return backslash_test


@baker.command
def get_failed_tests_by_name(test_name, exception_type=None, directory=None):
    """
    1. Get all failed tests objects
    2. Create html table
    3. Save html to file. if directory specified, file will be created in dir, otherwise tempdir
        is used by default
    :type test_name: str
    :type exception_type: str
    :type directory: str
    """
    tests = get_failed_tests(test_name, exception_type)
    html_text = create_tests_table(tests)
    file_name = f"{test_name}_{exception_type}_{arrow.now().timestamp}.html"
    save_to_file(file_name, html_text, directory)


def save_to_file(file_name, file_content, directory=None):
    """
    Save given data to specified path and notify about file creation
    :type file_name: str
    :type file_content: str
    :type directory
    """
    dest_dir = directory if directory else tempfile.gettempdir()
    file_path = os.path.join(dest_dir, file_name)
    with open(file_path, 'w') as file_handle:
        file_handle.write(file_content)
        log.notice(f"File was created at: {file_path}")


def create_tests_table(tests):
    """
    Generate html table as string, using predefined styles
    :type tests: list(backslash.test.Test)
    :rtype: str
    """
    html_text = config.table_style
    cell = config.cell_style
    html_text += f"<tr>{''.join([cell.format(value) for value in tests[0].__dict__.keys()])}</tr>"
    for test in tests:
        html_text += "<tr>"
        html_text += ''.join([cell.format(value) for value in test.__dict__.values()])
        html_text += "</tr>"
    html_text += "</table>"
    return html_text


def get_failed_tests(test_name, exception_type):
    """
    1. Query tests by name - get only failed tests
    2. Remove tests that appear running and interrupted
    3. If exception type was specified,
    :type test_name: str
    :type exception_type: str
    :rtype [InternalTest]
    """
    tests = query_tests_by_name(test_name)
    failed_tests = [test for test in tests if test.status not in ["RUNNING", "INTERRUPTED"]]
    if exception_type:
        tests_with_exception = []
        log.info(f"Filtering out tests that failed on {exception_type}...")
        for test in failed_tests:
            exception_info = _test_errors_contain_exception(test, exception_type)
            if exception_info:
                tests_with_exception.append(InternalTest(test, exception_info))
        return tests_with_exception
    return [InternalTest(test) for test in failed_tests]


def _test_errors_contain_exception(test, exception_type):
    """
    Check if test's errors contains specified exception
    1. Iterate though all test errors
    2. If the error exception type matches, return the error
    :type test: backslash.test.Test
    :type exception_type: str
    :rtype backslash.error.Error
    """
    for test_error in query_errors(test):
        if test_error._data['exception_type'] and \
                test_error._data['exception_type'].lower() == exception_type.lower():
            return test_error


def query_errors(test):
    """
    1. If there's a first error in the test (means it has errors)
    2. Check whether the test errors are in cache
    3. If in cache, return errors list
    4. If missing, query backslash, convert the LazyQuery to list and add to cache
    5. return the list of errors
    :type backslash.test.Test
    :rtype list(backslash.error.Error)
    """
    if test._data.get('first_error'):
        test_error_key = f"{test.id}_errors"
        log.info(f"Looing for test errors for {test.id} in cache")
        errors = get_from_cache(test_error_key)
        if errors:
            log.info(f"Found errors for {test.id}")
        else:
            log.info(f"Could not find errors for {test.id}")
            errors = [error for error in test.query_errors()]
            add_errors_to_cache(errors, test)
            add_to_cache(test_error_key, errors)
            return errors
    log.info(f"Test {test.id} doesn't contain errors'")


def add_errors_to_cache(errors, test):
    """
    Update list of tests related to the specific error in cache
    :type errors: list(backslash.error.Error)
    :type test: backslash.test.Test
    """
    for error in errors:
        exception_info = _get_exception_type(error)
        update_cache(exception_info, test.id)


@baker.command
def find_test_by_error(exception_type, directory=None):
    """
    1. Look for cache for entry with the specified exception type
    2. If entry found:
        2.1 Iterate through test id and obtain their test objects

    :type exception_type: str
    :type directory: str
    """
    test_ids = get_from_cache(exception_type)
    if test_ids:
        tests = [InternalTest(get_test(test_id)) for test_id in test_ids]
        html_text = f"<b>{exception_type} - {len(test_ids)} tests</b><br>"
        html_text += create_tests_table(tests)
        save_to_file(f"{exception_type}_{arrow.now().timestamp}.html", html_text, directory)


def get_latest_sessions(days_shift=1, show_successful=False):
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


def _get_exception_type(error):
    """
    return exception type if there's one, else return misc
    :type error: backslash.error.Error
    :type: str
    """
    exception_type = error._data["exception_type"]
    if not exception_type:
        exception_type = "Misc"
    return exception_type


@baker.command
def obtain_all_test_errors():
    """
    1. Get latest sessions
    2. get all tests in the list
    3. filter out successful tests and test that were executed using local auto code
    4. Update tests with errors
    """

    def update_errors():
        """
        1. iterate on test errors
        2. Add tests to list, if the error already exists in the dict, or create a new key in the
            dict and start a new test list
        3. In case exception type is missing from the error, the error would be classified as Misc
        """
        for error in query_errors(test):
            if error:
                exception_type = _get_exception_type(error)
                if exception_type in test_and_errors and test not in test_and_errors[exception_type]:
                    test_and_errors[exception_type].append(test)
                else:
                    test_and_errors[exception_type] = [test]

    sessions = get_latest_sessions()
    all_tests = list(chain.from_iterable([get_session_tests(session) for session in sessions]))
    failed_tests = [test for test in all_tests if test_matches_requirements(test)]
    test_and_errors = {}
    for test in failed_tests:
        update_errors()

    html_text = ''
    for error_name, tests in test_and_errors.items():
        internal_tests = [InternalTest(test) for test in tests]
        html_text += f"<b>{error_name}</b><br>"
        html_text = f"{html_text}<br>{create_tests_table(internal_tests)} <br>"
    save_to_file("errors.html", html_text)


def test_matches_requirements(test):
    """
    Return True if test is failed and wasn't executed from local branch
    :type test: backslash.test.Test
    :rtype: bool
    """
    return not test._data['is_interactive'] and\
           test.status in ["FAILURE", "ERROR"] and\
           not test._data['scm_dirty'] and\
           (not test._data['scm_local_branch'] or "/" not in test._data['scm_local_branch'])


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
        add_to_cache(session_key, tests, days_to_keep=2)
        for test in tests:
            add_to_cache(test.id, test)
    return tests


if __name__ == '__main__':
    baker.run()