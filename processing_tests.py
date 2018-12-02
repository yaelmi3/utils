import arrow

import config
from elastic_search_queries import ElasticSearch, InternalTest
from jira_queries import get_jira_tickets


def get_sorted_tests_list(**kwargs):
    return _sort_tests([test for test in get_tests(**kwargs)])


def _project_is_automation(test):
    """
    Return True:
        1. If project is specified in the session metadata as required - for new infra tests
        2. In case infinitest-version is among session metadata keys - for old infra tests
        3. if the word suite appears in the commandline, but the project isn't specified - this is
            for suite executions where the project isn't specified
    :type test: dict
    :rtype: bool
    """
    session_metadata = test['_source']['session_metadata']
    return (session_metadata.get("Project") and session_metadata["Project"] in config.auto_projects) \
            or 'infinitest-version' in session_metadata \
            or "suite" in session_metadata['slash::commandline'] and not session_metadata.get("Project")


def get_tests(**kwargs):
    """
    1. Get results from elastic search
    2. Convert tests to InternalTest object, in case test_params=False, the InternalTest object will
        be initiated without test parameters
    3. If the request is without test_params, squash tests based on identical name, to avoid
        repetitions
    """

    def test_should_be_added(test, coverage):
        """
        Test should be added to the list under the following conditions:
        1. If we need the tests with their params, all the tests will be added, hence return True
        2. In case params are not required, and the test is already in the list, no need to add it,
            hence return False
        3. In case params are not required, but the test is not in the list, add it to the list
            and return True
        :type test: dict
        :rtype: bool
        """
        if coverage or _project_is_automation(test):
            if test_params:
                return True

            test_full_name = f"{test['_source']['test']['file_name']}:{test['_source']['test']['name']}"
            status = test['_source']['status']
            if test_full_name not in test_names or status != test_names[test_full_name]:
                test_names.update({test_full_name: status})
                return True

    elastic_search = ElasticSearch()
    meta_tests = elastic_search.get_test_results(**kwargs)
    with_jira_tickets = kwargs.get('with_jira_tickets')
    test_params = kwargs.get('test_params', True)
    test_names = {}
    for meta_test in meta_tests:
        if test_should_be_added(meta_test, kwargs.get("coverage")):
            yield InternalTest(meta_test, test_params=test_params, jira_tickets=with_jira_tickets)


def additional_processing(tests, kwargs):
    """
    1. Remove tests that contain omitted errors
    2. Query JIRA and attach tickets to InternalTest objects
    :type tests: [InternalTest]
    :type kwargs: dict
    """
    if kwargs.get('with_jira_tickets'):
        for test in tests:
            get_jira_tickets(test)


def _sort_tests(tests):
    """
    sort tests by start time
    :type tests: list
    :rtype: list
    """
    tests.sort(key=lambda test: arrow.get(test.start_time, 'DD-MM-YY HH:mm:ss').timestamp,
               reverse=True)
    return tests
