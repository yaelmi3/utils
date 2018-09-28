import baker
import config
import reporting
from elastic_search_queries import process_error
from processing_tests import get_tests
from slash_tests import get_latest_tests
from test_stats import get_related_tests_from_cache, divide_tests_by_filename, get_tests_stats


def _matches_requirements(test):
    """
    Return True if test is failed and wasn't executed from local branch
    :type test: backslash.test.Test
    :rtype: bool
    """
    return test.test_name.startswith('test_') and not [branch_name for branch_name in
                                                       config.ignore_branches if
                                                       branch_name in test.branch]


@baker.command
def suites_overview(*send_email):
    """
    Obtain the latest tag and display tests grouped by their test suites
    """
    tag_tests = get_latest_tests()
    tests_by_suites = {"No Suite": []}
    if tag_tests:
        for test_key, tests in tag_tests.items():
            suite_names = tests[0]['test_suite']
            if not suite_names:
                tests_by_suites["No Suite"].append(test_key)
            else:
                for suite_name in suite_names:
                    if suite_name in tests_by_suites:
                        tests_by_suites[suite_name].append(test_key)
                    else:
                        tests_by_suites[suite_name] = [test_key]
    final_html = reporting.create_suites_table(tests_by_suites)
    return reporting.handle_html_report(final_html, send_email, message="Tests grouped by suites")


@baker.command
def find_test_by_error(exception, with_jira_tickets=False, *send_email):
    """
    1. Look for cache for entry with the specified exception type
    2. If entry found:
        2.1 Iterate through test id and obtain their test objects
    :type exception: str
    :type send_email: str
    """
    test_params = not with_jira_tickets
    tests = get_tests(error=exception, with_jira_tickets=with_jira_tickets,
                      status=config.failed_statuses, test_params=test_params)
    html_text = f"<b>{exception} - {len(tests)} tests</b><br>"
    html_text += reporting.create_tests_table(tests)
    return reporting.handle_html_report(html_text, send_email,
                                        message=f"Results exception {exception}")


@baker.command
def get_failed_tests_by_name(test_name, exception=None, with_jira_tickets=False, *send_email):
    """
    1. Get all failed tests objects
    2. Create html table
    3. Save html to file. if directory specified, file will be created in dir, otherwise tempdir
        is used by default
    :type test_name: str
    :type exception: str
    :type with_jira_tickets: bool
    :type send_email: tuple
    """
    tests = get_tests(test_name=test_name, error=exception,
                      status=config.failed_statuses, with_jira_tickets=with_jira_tickets)
    html_text = reporting.create_tests_table(tests)
    return reporting.handle_html_report(html_text, send_email,
                                        message=f"Results for test {test_name}")


@baker.command
def test_stats(test_name):
    """
    Get full summary of all test executions
    :type test_name: str
    """
    html_report = ''
    test_details = get_related_tests_from_cache(test_name)
    queried_tests = get_tests(test_name=test_name, status=config.all_statuses)
    if queried_tests:
        tests_by_file_name = divide_tests_by_filename(queried_tests)
        for file_name, tests in tests_by_file_name.items():
            html_report += get_tests_stats(test_name, file_name, tests, test_details)
    else:
        html_report = f"<br><br> No tests were found by this name: {test_name}"
    return html_report


@baker.command
def obtain_all_test_errors(days=1, with_jira_tickets=True, *send_email):
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
        for error in test._errors:

            if error['message'] in config.omit_errors:
                if test in updated_failed_tests:
                    updated_failed_tests.remove(test)
            else:
                exception_type = process_error(error)
                if exception_type in test_and_errors and test not in test_and_errors[exception_type]:
                    test_and_errors[exception_type].append(test)
                else:
                    test_and_errors[exception_type] = [test]
    test_and_errors = {}
    test_params = False if with_jira_tickets else True
    all_tests = get_tests(days=days,
                          status=config.failed_statuses,
                          with_jira_tickets=with_jira_tickets,
                          test_params=test_params)
    failed_tests = [test for test in all_tests if _matches_requirements(test)]
    updated_failed_tests = failed_tests
    for test in failed_tests:
        update_errors()
    final_html = reporting.create_errors_table(test_and_errors, updated_failed_tests)
    return reporting.handle_html_report(final_html, send_email)


if __name__ == '__main__':
    baker.run()
