import ast
import glob
import os
import subprocess

import baker

import log
from cache_client import redis_cache, add_to_cache, get_from_cache
from exceptions import document_exception
from git_utils import get_latest_tag


def get_suite_files(suite_directory):
    """
    Iterate through the given suite directory and return all its files
    :type suite_directory: str
    :rtype: list(str)
    """
    return [full_path for full_path in
            glob.iglob(f'{suite_directory}/**/*.suite', recursive=True) if
            "all_tests.suite" not in full_path]


@redis_cache
def get_all_tests(git_tag, infinibox_tests_path):
    log.info(f"Processing all tests by executing slash list for version: {git_tag}")
    test_lines = str(subprocess.check_output(["./get_slash_lists.sh", "slash_list_tests"])).split("\\n")[:-1]
    test_bulk = [test_line for test_line in test_lines if not test_line.startswith("tests/examples")]
    tests_by_suite = dict()
    all_suites = get_suite_files(os.path.join(infinibox_tests_path, 'suites'))
    for index, suite_file in enumerate(all_suites):
        log.info(f"Processing {suite_file} ({index + 1}/{len(all_suites)})")
        tests_by_suite[os.path.basename(suite_file)] = str(
            subprocess.check_output(
                ["./get_slash_lists.sh", "slash_list_suite", suite_file])).split("\\n")[:-1]
    return parse_tests(test_bulk, tests_by_suite)


def parse_tests(tests_bulk, tests_in_suite):
    """
    Parse list of tests into Test objects and combine them with test suites
    :type tests_bulk: list
    :type tests_in_suite: dict
    :rtype: dict
    """
    old_convention_indicator = "before:"
    tests = dict()
    for test_line in tests_bulk:
        with document_exception(message=f"Failed to process test ine {test_line}"):
            test_class = params_dict = None
            full_test, tags = test_line.split("  Tags: ")
            if old_convention_indicator in full_test:
                test_path, test_class_name_and_params = full_test.split(":", 1)
                test_class, test_and_params = test_class_name_and_params.split('.')
            else:
                test_path, test_and_params = full_test.split(":")

            if '(' in test_and_params:
                test_name, params_str = test_and_params.split('(')
                params_dict = _convert_params_to_dict(params_str)
            else:
                test_name = test_and_params
            test_key = f"{test_path}:{test_name}" if not test_class else f"{test_path}:{test_class}.{test_name}"
            test_suite = _obtain_suite_name(test_key, tests_in_suite)
            test = {"test_name": test_name,
                    "test_path": test_path,
                    "tags": ast.literal_eval(tags),
                    "params_dict": params_dict,
                    "test_class": test_class,
                    "test_suite": test_suite}
            if test_key in tests:
                tests[test_key].append(test)
            else:
                tests[test_key] = [test]
    return tests


def _convert_params_to_dict(params_bulk):
    """
    Convert param string: "(foo=bar)" into dict: {"foo": "bar"}
    :type params_bulk: str
    :rtype: dict
    """
    params = params_bulk.replace(')', '').split(',')
    return {elem.split('=', 1)[0]: elem.split('=', 1)[1].strip() for elem in
            params}


def _obtain_suite_name(test_key, tests_in_suite):
    return [suite_name for suite_name, suite_tests in tests_in_suite.items() if
            any(suite_test for suite_test in suite_tests if test_key in suite_test)]


@baker.command
def get_updated_tests(working_tree_dir, env_dir):
    """
    1. Get latest tag from infinibox_tests by running git describe
    2. Using this key, check whether tests were already cached
    3. If cached, return list of tests, otherwise obtain and process the tests using slash list
    :rtype: list
    """
    git_tag = get_latest_tag(working_tree_dir)
    current_tag = {'tag_main_ver': git_tag.split('.',1)[0], "tag_revision": git_tag.split('-')[1]}
    os.environ["INFINIBOX_TESTS"] = working_tree_dir
    os.environ["ENV_PATH"] = os.path.join(env_dir, 'bin/activate')
    get_all_tests(str(current_tag), working_tree_dir)
    _update_latest_tag_in_cache(current_tag)


def _update_latest_tag_in_cache(current_tag_ver):
    """
    1. Get latest tag from cache
    2. If the current tag ver is greater than latest, update it
    :type current_tag_ver: dict
    """
    latest_tag_ver_str = get_from_cache("latest_tag")
    latest_tag_ver = ast.literal_eval(latest_tag_ver_str)
    if not latest_tag_ver or \
            int(current_tag_ver['tag_main_ver']) > int(latest_tag_ver['tag_main_ver']) or \
                (int(current_tag_ver['tag_revision']) > int(latest_tag_ver['tag_revision']) and
                    int(current_tag_ver['tag_main_ver']) == int(latest_tag_ver['tag_main_ver'])):
        log.info(f"Current tag {current_tag_ver} is more up to the date that the saved: {latest_tag_ver}")
        add_to_cache("latest_tag", str(current_tag_ver), days_to_keep=20)
    else:
        log.info(f"Saved tag {latest_tag_ver} is already up to date. Current tag: {current_tag_ver}")


def get_latest_tests():
    latest_tag = get_from_cache("latest_tag")
    if latest_tag:
        return get_from_cache(str(latest_tag))


if __name__ == '__main__':
    log.init_log(log_file=False)
    baker.run()