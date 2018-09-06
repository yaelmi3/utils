import baker

import config
from elastic_search_queries import process_error
from processing_tests import get_tests
from reporting import handle_html_report, create_tests_table, create_errors_table, \
    create_test_stats_table


def _test_matches_requirements(test):
    """
    Return True if test is failed and wasn't executed from local branch
    :type test: backslash.test.Test
    :rtype: bool
    """
    return test.test_name.startswith('test_') and not [branch_name for branch_name in
                                                       config.ignore_branches if
                                                       branch_name in test.branch]


@baker.command
def find_test_by_error(exception, with_jira_tickets=False, *send_email):
    """
    1. Look for cache for entry with the specified exception type
    2. If entry found:
        2.1 Iterate through test id and obtain their test objects

    :type exception: str
    :type send_email: str
    """
    test_params = False if with_jira_tickets else True
    tests = get_tests(error=exception, with_jira_tickets=with_jira_tickets,
                      status=config.failed_statuses, test_params=test_params)
    html_text = f"<b>{exception} - {len(tests)} tests</b><br>"
    html_text += create_tests_table(tests)
    return handle_html_report(html_text, send_email, message=f"Results exception {exception}")


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
    html_text = create_tests_table(tests)
    return handle_html_report(html_text, send_email, message=f"Results for test {test_name}")


@baker.command
def test_history(test_name):
    """
    Get full summary of all test executions
    :type test_name: str
    """
    header = f'Stats for <a href="{config.backslash_url}#/tests?search={test_name}">{test_name}</a>'
    test_analysis = {}
    tests = get_tests(test_name=test_name, status=config.all_statuses)
    successful_tests = [test for test in tests if test._status == "SUCCESS"]
    failed_tests = [test for test in tests if test._status in config.failed_statuses]
    test_analysis["Total test runs"] = len(tests)
    test_analysis["Successful runs"] = len(successful_tests)
    test_analysis["Failed runs"] = len(failed_tests)
    success_ratio = int(
        100 * float(test_analysis["Successful runs"]) / float(test_analysis["Total test runs"]))
    test_analysis["Test ratio"] = f'{success_ratio}% success'
    test_analysis[
        "Last failure"] = f"Occurred on {failed_tests[0].start_time}," \
                          f" version: {failed_tests[0].version}, link: {failed_tests[0].test_link}"
    return create_test_stats_table(header=header, test_analysis=test_analysis)


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

            if error['message'] not in config.omit_errors:
                exception_type = process_error(error)
                if exception_type in test_and_errors and test not in test_and_errors[exception_type]:
                    test_and_errors[exception_type].append(test)
                else:
                    test_and_errors[exception_type] = [test]
            else:
                if test in updated_failed_tests:
                    updated_failed_tests.remove(test)
    test_and_errors = {}
    test_params = False if with_jira_tickets else True
    all_tests = get_tests(days=days,
                          status=config.failed_statuses,
                          with_jira_tickets=with_jira_tickets,
                          test_params=test_params)
    failed_tests = [test for test in all_tests if _test_matches_requirements(test)]
    updated_failed_tests = failed_tests
    for test in failed_tests:
        update_errors()
    final_html = create_errors_table(test_and_errors, updated_failed_tests)
    return handle_html_report(final_html, send_email)


if __name__ == '__main__':
    baker.run()