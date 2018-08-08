import os
import tempfile

import arrow
import baker

import config
from elastic_search_queries import get_failed_tests, process_error
from config import log


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
    if tests:
        cell = config.cell_style
        html_text += f"<tr>{''.join([cell.format(value) for value in tests[0].__dict__.keys() if not value.startswith('_')])}</tr>"
        for test in tests:
            html_text += "<tr>"
            html_text += ''.join(
                [cell.format(value) for key, value in test.__dict__.items() if not key.startswith('_')])
            html_text += "</tr>"
        html_text += "</table>"
        return html_text
    log.error("Could not find tests that match the query")
    return ''


def _test_matches_requirements(test):
    """
    Return True if test is failed and wasn't executed from local branch
    :type test: backslash.test.Test
    :rtype: bool
    """
    return test.test_name not in ['Interactive', 'mayhem'] and '/' not in test.branch


@baker.command
def obtain_all_test_errors(days=1):
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
            exception_type = process_error(error)
            if exception_type in test_and_errors and test not in test_and_errors[exception_type]:
                test_and_errors[exception_type].append(test)
            else:
                test_and_errors[exception_type] = [test]

    test_and_errors = {}
    all_tests = get_failed_tests(days=days, status=config.failed_statuses)
    failed_tests = [test for test in all_tests if _test_matches_requirements(test)]
    for test in failed_tests:
        update_errors()
    html_text = ''
    for error_name, tests in test_and_errors.items():
        html_text += f"<b>{error_name}</b><br>"
        html_text = f"{html_text}<br>{create_tests_table(tests)} <br>"
    save_to_file("errors.html", html_text)


@baker.command
def find_test_by_error(exception_type, directory=None):
    """
    1. Look for cache for entry with the specified exception type
    2. If entry found:
        2.1 Iterate through test id and obtain their test objects

    :type exception_type: str
    :type directory: str
    """
    tests = get_failed_tests(error=exception_type, status=config.failed_statuses)
    html_text = f"<b>{exception_type} - {len(tests)} tests</b><br>"
    html_text += create_tests_table(tests)
    save_to_file(f"{exception_type}_{arrow.now().timestamp}.html", html_text, directory)


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
    tests = get_failed_tests(test_name=test_name, error=exception_type)
    html_text = create_tests_table(tests)
    file_name = f"{test_name}_{exception_type}_{arrow.now().timestamp}.html"
    save_to_file(file_name, html_text, directory)


if __name__ == '__main__':
    baker.run()