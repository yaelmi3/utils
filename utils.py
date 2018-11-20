import os
import time
from collections import OrderedDict, namedtuple

import arrow
import baker

import config
import log
import reporting
from coverage import determine_flaky_tests, update_errors
from elastic_search_queries import process_error
from jira_queries import get_ticket_status
from processing_tests import get_tests, get_sorted_tests_list
from slash_tests import get_latest_tests
from test_stats import get_related_tests_from_cache, divide_tests_by_filename, get_tests_stats

COMMAND_OUTPUT = namedtuple("CommandOutput", 'html file_name')


def _matches_requirements(test):
    """
    Return True if test is failed and wasn't executed from local branch
    :type test: backslash.test.Test
    :rtype: bool
    """
    return test.test_name.startswith('test_') and not [branch_name for branch_name in
                                                       config.ignore_branches if
                                                       branch_name in test.branch]


def _get_test_blocker(test):
    if 'jira-blocker' in test['tags']:
        return test['tags'][test['tags'].index('jira-blocker') + 1]
    return ''


@baker.command
def coverage_by_version(version, include_simulator=False, save_static_link=False, save_to_db=None):
    """
    1. Get all tests executed on specific version
    2. Get all tests from repo
    3. Create copy of tests repo not_covred list
    3. Iterate through all the tests
        3.1 If test exists in repo, remove it form the not covered list
        3.2 Based on the test result, add it to the test dict that separates success and faulire
        3.3 Gather all errors in the tests
    4 Determine flaky tests
    5. Generate report
    """
    version = version.strip()
    repo_tests = {key_name: tests for key_name, tests in get_latest_tests().items() if
                      not key_name.startswith("tests/test_utils_tests")}

    tests = get_tests(version=version, include_simulator=include_simulator,
                      status=config.all_statuses)

    executed_tests = {"SUCCESS": {},
                      'ERROR': {},
                      f"Last_{config.definite_executions_threshold}_SUCCESS": {},
                      f"Last_{config.definite_executions_threshold}_ERROR": {}}
    errors = {}
    if tests and repo_tests:
        not_covered = repo_tests.copy()
        for index, test in enumerate(tests):
            log.debug(f"{index} : {test.start_time}")
            log.debug(test.test_name)
            for test_key in repo_tests:
                if test.test_name in test_key and test._file_name in test_key:
                    if test_key in not_covered:
                        not_covered.pop(test_key)
                    if test_key in executed_tests[test._status]:
                        executed_tests[test._status][test_key].append(test.start_time)
                    else:
                        executed_tests[test._status][test_key] = [test.start_time]
                    update_errors(test, errors)
        flaky_tests = determine_flaky_tests(executed_tests, repo_tests)
        coverage_data = {'not_executed': [test_key for test_key, test_list in not_covered.items() if not _get_test_blocker(test_list[0])],
                         'blocked': [test_key for test_key, test_list in not_covered.items() if _get_test_blocker(test_list[0])],
                         'flaky': flaky_tests}
        coverage_data.update(executed_tests)
        html_text = reporting.create_coverage_report(header=f"Coverage for version {version}",
                                                coverage_data=coverage_data, errors=errors)
        file_name = f"{version.replace('.', '_')}__coverage_report" \
                    f"_{arrow.now().format('DD-MM-YY_HH-mm-ss')}.html"
        if save_to_db:
            save_to_db = "coverage_reports"
        return COMMAND_OUTPUT(reporting.handle_html_report(html_text,
                                                           save_as_file=save_static_link,
                                                           message=f"Coverage for version {version}",
                                                           save_to_redis=save_to_db,
                                                           file_name=file_name), '')


@baker.command
def show_jira_blockers(save_static_link=False):
    """
    Display all tests that are currently blocked and sort them by ticket statuses
    :type save_static_link: str
    :rtype: str
    """
    tests = get_latest_tests()
    if tests:
        blocked_tests = {}
        for test_key, test_list in tests.items():
            test_blocker = _get_test_blocker(test_list[0])
            if test_blocker:
                status = get_ticket_status(test_blocker)
                if status in blocked_tests:
                    blocked_tests[status].append(
                        {'test': test_key, 'test_blocker': config.jira_link.format(test_blocker),
                         'status': status})
                else:
                    blocked_tests[status] = [
                        {'test': test_key, 'test_blocker': config.jira_link.format(test_blocker),
                         'status': status}]
        sorted_blocked_tests = OrderedDict(sorted(blocked_tests.items(), reverse=True))
        html_text = reporting.create_test_blockers_table(sorted_blocked_tests)
        return COMMAND_OUTPUT(reporting.handle_html_report(html_text, save_as_file=save_static_link,
                                                           message="Latest test blockers"), '')


@baker.command
def suites_overview(save_static_link=False):
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
    return COMMAND_OUTPUT(
        reporting.handle_html_report(final_html, save_as_file=save_static_link,
                                     message="Tests grouped by suites"), '')


@baker.command
def find_tests_by_name_in_repo(partial_test_name, create_suite_file=False, include_dir_names=True,
                               save_static_link=False):
    """
    Locate all tests in repo that contain specified string and (optionally) generate a suite file
     from these tests
    """
    partial_test_name = partial_test_name.strip()
    tag_tests = get_latest_tests()
    file_name = ''
    if tag_tests:
        if include_dir_names:
            selected_tests = set(test_key for test_key, _ in tag_tests.items() if partial_test_name in test_key)
        else:
            selected_tests = set(test_key for test_key, tests in tag_tests.items() if
                                 partial_test_name in test_key and partial_test_name in tests[0]['test_name'])
        if create_suite_file:
            suite_tests = '\n'.join(selected_tests)
            file_path = reporting.save_to_file(suite_tests,
                                               f"{partial_test_name}_{int(time.time())}.suite")
            file_name = os.path.basename(file_path)
        html_report = reporting.create_tests_list(selected_tests,
                                                  f'{len(selected_tests)} tests were found matching "{partial_test_name}"')

        return COMMAND_OUTPUT(
            reporting.handle_html_report(html_report, save_as_file=save_static_link), file_name)


@baker.command
def find_test_by_error(error_name, with_jira_tickets=False, include_simulator=False,
                       save_static_link=False):
    """
    1. Look for cache for entry with the specified exception type
    2. If entry found:
        2.1 Iterate through test id and obtain their test objects
    :type error_name: str
    :type send_email: str
    :type include_simulator: bool
    """
    error_name = error_name.strip()
    test_params = not with_jira_tickets
    tests = get_sorted_tests_list(error=error_name,

                                  with_jira_tickets=with_jira_tickets,
                                  status=config.failed_statuses,
                                  test_params=test_params,
                                  include_simulator=include_simulator)
    html_text = f"<b>{error_name}:</b>"
    html_text += reporting.create_tests_table(tests)
    return COMMAND_OUTPUT(reporting.handle_html_report(html_text, save_as_file=save_static_link,
                                                       message=f"Results exception {error_name}"), '')

@baker.command
def get_failed_tests_by_name(test_name, exception=None, with_jira_tickets=False,
                             include_simulator=False, save_static_link=False):
    """
    1. Get all failed tests objects
    2. Create html table
    3. Save html to file. if directory specified, file will be created in dir, otherwise tempdir
        is used by default
    :type test_name: str
    :type exception: str
    :type with_jira_tickets: bool
    :type include_simulator: bool
    :type save_static_link: bool
    """
    test_name = test_name.strip()
    tests = get_sorted_tests_list(test_name=test_name, error=exception,
                                  status=config.failed_statuses,
                                  with_jira_tickets=with_jira_tickets,
                                  include_simulator=include_simulator)
    html_text = reporting.create_tests_table(tests)
    return COMMAND_OUTPUT(reporting.handle_html_report(html_text, save_as_file=save_static_link,
                                                       message=f"Results for test {test_name}"), '')


@baker.command
def test_stats(test_name, include_simulator=False, save_static_link=False):
    """
    Get full summary of all test executions
    :type test_name: str
    :type include_simulator: bool
    """
    test_name = test_name.strip()
    html_report = ''
    test_details = get_related_tests_from_cache(test_name)
    queried_tests = get_sorted_tests_list(test_name=test_name, status=config.all_statuses,
                                          include_simulator=include_simulator)
    if queried_tests:
        tests_by_file_name = divide_tests_by_filename(queried_tests)
        for file_name, tests in tests_by_file_name.items():
            html_report += get_tests_stats(test_name, file_name, tests, test_details)
    else:
        html_report = f"<br><br> No tests were found by this name: {test_name}"
    if save_static_link:
        return COMMAND_OUTPUT(reporting.save_to_file(html_report), file_name='')
    return COMMAND_OUTPUT(html_report, '')


@baker.command
def obtain_all_test_errors(days=1, with_jira_tickets=False, include_simulator=False,
                           save_static_link=False, *send_email):
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
    all_tests = get_sorted_tests_list(days=days,
                                      status=config.failed_statuses,
                                      with_jira_tickets=with_jira_tickets,
                                      test_params=test_params,
                                      include_simulator=include_simulator)
    failed_tests = [test for test in all_tests if _matches_requirements(test)]
    updated_failed_tests = failed_tests
    for test in failed_tests:
        update_errors()
    final_html = reporting.create_errors_table(test_and_errors, updated_failed_tests)
    return COMMAND_OUTPUT(reporting.handle_html_report(final_html, save_as_file=save_static_link,
                                                       send_email=send_email), '')


if __name__ == '__main__':
    baker.run()
