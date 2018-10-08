from cachetools import cached
from ecosystem.jira import client
from cachetools import TTLCache

import config
import log
from exceptions import document_exception


cache = TTLCache(maxsize=40000, ttl=60 * 60 * 2)


@cached(cache)
def _query_jira(query_string):
    return [ticket for ticket in client.search(config.jira_query.format(query_string))
            if query_string in ticket.get_summary() or
            (ticket.get_field("description") and query_string in ticket.get_field(
                "description"))]


def get_jira_tickets(test):
    """
    1. Get all jira tickets that contain test name
    2. Filter tickets that contain specifically the test name in summary and description
    3. Get all jira tickets that contain the errors in the test
    5. Search tickets by test id
    4. existing_jira_tickets keeps already the tickets that were queried. This specifically apply
        for repearing errors under different tests
    :type test: InternalTest
    """
    log.debug(f"Getting jira tickets for {test.test_name}")
    search_for_jira_tickets(test, test.test_name)
    for error in test._errors:
        error_message = error.get('message').replace("{", '').replace("}", '')
        if error_message not in config.generic_errors and len(error_message) < 150:
            log.debug(f"Getting jira tickets for error: {error_message}")
            search_for_jira_tickets(test, error_message)
    log.debug(f"Getting jira tickets for id {test._id}")
    search_for_jira_tickets(test, test._id)
    if test._related_tickets:
        test.related_tickets = '    '.join(
            {config.jira_link_status.format(ticket.key, ticket.get_resolution()) for ticket in
             test._related_tickets})


@cached(cache)
def get_ticket_status(test_blocker):
    with log.silence_log_output():
        issue = client.get_issue(test_blocker)
        return f"{issue.get_status()} - {issue.get_resolution()}"


def search_for_jira_tickets(test, query_string):
    """
    1. Silence the log
    2. Perform JIRA query and then verify that the specific, full string really appears in the
        summary or the description
    :type test: InternalTest
    :type query_string: str
    """
    with document_exception(), log.silence_log_output():
        tickets = _query_jira(query_string)
        test._related_tickets.extend(tickets)
