import arrow

import config
import log
from slash_tests import get_latest_tests
from reporting import create_test_stats_table

DETAIL_NAMES = ['test_suite', 'tags', 'test_params']
NA = 'N/A'

def _get_duration_average(test_list):
    """
    return average of test execution duration
    :type test_list: list
    :rtype: str
    """
    return arrow.get(sum([test._duration for test in test_list])/len(test_list)).format('HH:mm:ss') if test_list else NA


def get_related_tests_from_cache(test_name):
    """
    return latest tests details saved in redis cache
    :type test_name: str
    :rtype: dict
    """
    tests = get_latest_tests()
    return {test_key: tests for test_key, tests in tests.items() if test_name in test_key}


def divide_tests_by_filename(tests):
    """
    Get list of tests and in divide them by their internal filenames. In most cases, this will
    result in a singled key dict
    :type tests: list
    :rtype: dict
    """
    tests_by_path = {}
    for test in tests:
        if test.test_module in tests_by_path:
            tests_by_path[test.test_module].append(test)
        else:
            tests_by_path[test.test_module] = [test]
    return tests_by_path


def _get_additional_details(test_name, file_name, test_details):
    """
    1. get tests that match both name and file path
    2. Squash all test params and add it to the single details dict that reflects full test
    :type test_name: str
    :type file_name: str
    :type test_details: dict
    :rtype: dict
    """

    try:
        related_tests = next(tests for test_key, tests in test_details.items() if test_name in test_key and file_name in test_key)
    except StopIteration:
        log.warning(f"Could not find {test_name}-{file_name} in updated tests")
        return {detail: NA for detail in DETAIL_NAMES}
    details = related_tests[0]
    details['test_params'] = [test.get('params_dict') for test in related_tests]
    details['test_suite'] = ', '.join(details.get('test_suite')) if details.get('test_suite') else None
    return details


def get_tests_stats(test_name, file_name, tests, test_details):
    """
    Analyze and return test analysis result in html format
    :type test_name: str
    :type file_name: str
    :type tests: list
    :type test_details: dict
    :rtype: str
    """
    last_execution = "Occurred on {0}, version: {1}, link: {2}, parameters: {3}"
    required_values = ["start_time", "version", "test_link", "parameters"]
    test_analysis = {}
    note = None
    header = f'Stats for {config.tests_search_link.format(test_name)} - {file_name}'
    successful_tests = [test for test in tests if test._status == "SUCCESS"]
    failed_tests = [test for test in tests if test._status in config.failed_statuses]
    test_analysis["total_test_runs"] = len(tests)
    test_analysis["successful_runs"] = len(successful_tests)
    test_analysis["failed_runs"] = len(failed_tests)
    test_analysis['average_execution_time'] = _get_duration_average(successful_tests)
    if test_analysis["total_test_runs"] > 0:
        success_ratio = int(
            100 * float(test_analysis["successful_runs"]) / float(test_analysis["total_test_runs"]))
    else:
        success_ratio = 100
    test_analysis["test_ratio"] = f'{success_ratio}% success'
    details = _get_additional_details(test_name, file_name, test_details)
    for detail in DETAIL_NAMES:
        test_analysis[detail] = details.get(detail)
    if NA in details.values():
        note = "This test no longer part of the current Automation code"
    for last_runs, test_group in {"last_failure": failed_tests,
                                  "last_success": successful_tests}.items():
        test_analysis[last_runs] = last_execution.format(
            *[getattr(test_group[0], value) for value in
              required_values]) if test_group else "N/A"
    return create_test_stats_table(header=header, test_analysis=test_analysis, note=note)