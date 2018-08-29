import arrow
from ecosystem.jira import client

import config
from elastic_search_queries import ElasticSearch, InternalTest
from exceptions import document_exception
from logs import silence_log_output, log


def get_failed_tests(**kwargs):
    """
    1. Get results from elastic search
    2. Convert tests to InternalTest object, in case test_params=False, the InternalTest object will
        be initiated without test parameters
    3. If the request is without test_params, squash tests based on identical name, to avoid
        repetitions
    """

    def test_should_be_added(test):
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
        test_name = test['_source']['test']['name']
        if test_name.startswith('test_'):
            if test_params:
                return True
            if test_name not in test_names:
                test_names.append(test_name)
                return True


    elastic_search = ElasticSearch()
    failed_tests_meta = elastic_search.get_failed_tests_results(**kwargs)
    test_params = kwargs.get("test_params", True)
    test_names = []
    tests = _sort_tests(
        [InternalTest(test, test_params=test_params, jira_tickets=kwargs.get('attach_jira_ticket'))
                         for test in failed_tests_meta if test_should_be_added(test)])
    additional_processing(tests, kwargs)
    return tests


def additional_processing(tests, kwargs):
    """
    Query JIRA and attach tickets to InternalTest objectsת ןכ רק/וןרקג
    :type tests: [InternalTest]
    :type kwargs: dict
    """
    if kwargs.get('attach_jira_ticket'):
        existing_jira_tickets = {}
        for test in tests:
            get_jira_tickets(test, existing_jira_tickets)


def _sort_tests(tests):
    """
    sort tests by start time
    :type tests: list
    :rtype: list
    """
    tests.sort(key=lambda test: arrow.get(test.start_time, 'DD-MM-YY HH:mm:ss').timestamp,
               reverse=True)
    return tests


def search_for_jira_tickets(test, query_string, existing_jira_tickets):
    """
    1. Silence the log
    2. Perform JIRA query and then verify that the specific, full string really appears in the
        summary or the description
    :type test: InternalTest
    :type query_string: str
    :type existing_jira_tickets: dict
    """
    with document_exception(), silence_log_output():
        tickets = [ticket for ticket in client.search(config.jira_query.format(query_string))
                if query_string in ticket.get_summary() or
                (ticket.get_field("description") and query_string in ticket.get_field("description"))]
        test._related_tickets.extend(tickets)
        existing_jira_tickets[query_string] = tickets


def get_jira_tickets(test, existing_jira_tickets):
    """
    1. Get all jira tickets that contain test name
    2. Filter tickets that contain specifically the test name in summary and description
    3. Get all jira tickets that contain errors
    4. existing_jira_tickets keeps already the tickets that were queried. This specifically apply
        for repearing errors under different tests
    :type test: InternalTest
    :type existing_jira_tickets: dict
    """
    if test.test_name in existing_jira_tickets:
        log.info(f"Tickets for {test.test_name} were alaready obtained")
        test._related_tickets.extend(existing_jira_tickets[test.test_name])
    else:
        log.info(f"Getting jira tickets for {test.test_name}")
        search_for_jira_tickets(test, test.test_name, existing_jira_tickets)
    for error in test._errors:
        error_message = error.get('message').replace("{", '').replace("}", '')
        if error_message in existing_jira_tickets:
            test._related_tickets.extend(existing_jira_tickets[error_message])
        else:
            if error_message not in config.omit_errors and len(error_message) < 150:
                search_for_jira_tickets(test, error_message, existing_jira_tickets)
    if test._related_tickets:
        test.related_tickets = ' '.join(
            {config.jira_link.format(ticket.key) for ticket in test._related_tickets})