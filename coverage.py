import arrow

import config
import log
from elastic_search_queries import process_error


def determine_flaky_tests(executed_tests, all_repo_tests):
    """
    1. Determine flaky tests by getting tests that both failed and succeeded
    2. Iterate through flaky tests
    2.1 If test latest executions succeeded or failed config.runs_threshold times
        (including the params), the test will be considered 10_successful/failed
    2.2 Otherwise, tests will be considered flaky
    :type executed_tests: dict
    :type all_repo_tests: dict
    :rtype: list
    """

    def get_num_definite_runs(tested_status, static_status):
        num_of_definite_executions = 0
        last_test = arrow.get(executed_tests[static_status][flaky_test][0], 'DD-MM-YY HH:mm:ss')
        for index, success_time in enumerate(executed_tests[tested_status][flaky_test]):
            if arrow.get(success_time, 'DD-MM-YY HH:mm:ss') > last_test:
                if (index + 1) % num_tests == 0:
                    num_of_definite_executions += 1
            else:
                break
        if num_of_definite_executions >= config.definite_executions_threshold:
            log.info(
                f"{flaky_test} has ended with {tested_status}"
                f" {config.definite_executions_threshold} times")
            executed_tests[f"Last_{config.definite_executions_threshold}_{tested_status}"][
                flaky_test] = {"SUCCESS": len(executed_tests["SUCCESS"][flaky_test]),
                               "FAILURE": len(executed_tests["ERROR"][flaky_test])}
            del(executed_tests[static_status][flaky_test])
            del(executed_tests[tested_status][flaky_test])
            updated_flaky_tests.pop(flaky_test)
            return True

    flaky_tests = set([test_name for test_name in executed_tests['SUCCESS']]) & set(
        [test_name for test_name in executed_tests['ERROR']])
    updated_flaky_tests = {flaky_test: {'SUCCESS': len(executed_tests['SUCCESS'][flaky_test]),
                                        "FAILURE": len(executed_tests['ERROR'][flaky_test])}
                           for flaky_test in flaky_tests}
    for flaky_test in flaky_tests:
        num_tests = len(all_repo_tests[flaky_test])
        status_updated = get_num_definite_runs('SUCCESS', 'ERROR')
        if not status_updated:
            status_updated = get_num_definite_runs('ERROR', 'SUCCESS')

        if not status_updated:
            log.info(f"{flaky_test} will be considered Flaky")
            del (executed_tests['SUCCESS'][flaky_test])
            del (executed_tests['ERROR'][flaky_test])
    return updated_flaky_tests


def update_errors(test, errors):
    if test._status == "ERROR":
        for error in test._errors:
            processed_error = process_error(error, max_length=70)
            if processed_error in errors:
                errors[processed_error] += 1
            else:
                errors[processed_error] = 1
