import pickle
import sys
import arrow
import baker
import requests
from backslash import Backslash
from logbook import Logger, StreamHandler
from urlobject import URLObject

StreamHandler(sys.stdout).push_application()
_logger = Logger(__name__)

BACKSLASH_URL = "https://backslash.infinidat.com/"


class InternalTest(object):
    def __init__(self, backslash_test, exception_info=None, to_cache=True):
        self.test_link = f'<a href="{backslash_test.ui_url}">{backslash_test.logical_id}</a>'
        self.parameters =backslash_test._data['parameters']
        self.status = backslash_test._data['status']
        self.error = exception_info._data['exception_type'] if exception_info else \
        backslash_test._data['first_error']['exception_type']
        self.version = backslash_test._data['subjects'][0]['version']
        self.start_time = arrow.get(backslash_test._data['start_time']).format('DD-MM-YY HH:mm:ss')
        self.duration = arrow.get(backslash_test._data['duration']).format('HH:mm:ss')
        self.comment = backslash_test._data["last_comment"]['comment'] if backslash_test._data[
            'num_comments'] else ''
        if to_cache:
            self.update_cache(backslash_test)

    def update_cache(self, backslash_test):
        import ipdb; ipdb.set_trace()
        pickled_test = pickle.dumps(backslash_test)


def send_command_to_host(host, command, to_file=""):
    command_output = host.run_command(command, check=True).get_output_as_text().split('\n')
    for line in command_output:
        _logger.info(line)
    if to_file:
        output_to_file(to_file, command_output)


def output_to_file(file_name, output):
    with open(file_name, 'w') as output_file:
        for line in output:
            output_file.write(f"{line}\n")


def get_backslash_client():
    server_address = URLObject(BACKSLASH_URL)
    return Backslash(server_address, runtoken="2913:20216d54-dcd4-46ad-aeca-94b117a49710")


def locate_session(session_id):
    return get_backslash_client().query_sessions().filter(id=session_id)[0]


def query_tests_by_name(test_name, show_successful=False):
    backslash_client = get_backslash_client()
    query = f"{BACKSLASH_URL}/rest/tests?page_size=2000&search=name%3D{test_name}&show_abandoned=false&" \
            f"show_skipped=false&show_successful={str(show_successful).lower()}"
    _logger.info(f"Executing query: {query}")
    result = requests.get(query)
    if result.ok:
        meta_tests = result.json().get("tests")
        _logger.info(f"{len(meta_tests)} tests were found. Converting them to test objects")
        return [backslash_client.query_tests().filter(id=meta_test["id"])[0] for meta_test in meta_tests]


@baker.command
def generate_html_report(test_name, exception_type=None):
    html_text = '<style type="text/css"> .tg  {border-collapse:collapse;border-spacing:0;} ' \
                '.tg td{font-family:Arial, sans-serif;font-size:14px;padding:10px 5px;' \
                'border-style:solid;border-width:1px;overflow:hidden;word-break:normal;' \
                'border-color:black;} .tg th{font-family:Arial, sans-serif;font-size:14px;' \
                'font-weight:normal;padding:10px 5px;border-style:solid;border-width:1px;overflow:' \
                'hidden;word-break:normal;border-color:black;} .tg .tg-yw4l{vertical-align:top}' \
                ' </style> <table class="tg">'
    cell = '<th class="tg-yw4l">{}</th>'
    tests = get_failed_tests(test_name, exception_type)
    html_text += f"<tr>{''.join([cell.format(value) for value in tests[0].__dict__.keys()])}</tr>"
    for test in tests:
        html_text += "<tr>"
        html_text += ''.join([cell.format(value) for value in test.__dict__.values()])
        html_text += "</tr>"
    html_text += "</table>"
    file_path = f"{test_name}_{exception_type}_.html"
    with open(file_path, 'w') as html_file:
        html_file.write(html_text)
        _logger.notice(file_path)


def get_failed_tests(test_name, exception_type):
    """
    1. Query tests by name - return tests without successful
    2. Removing running tests from the list
    :type test_name: str
    :type exception_type: str
    :rtype [InternalTest]
    """
    tests = query_tests_by_name(test_name)
    failed_tests = [test for test in tests if test.status not in ["RUNNING", "INTERRUPTED"]]
    if exception_type:
        tests_with_exception = []
        _logger.info(f"Filtering out tests that failed on {exception_type}...")
        for test in failed_tests:
            exception_info = _test_errors_contain_exception(test, exception_type)
            if exception_info:
                tests_with_exception.append(InternalTest(test, exception_info))
        return tests_with_exception
    return [InternalTest(test) for test in failed_tests]


def _test_errors_contain_exception(test, exception_type):
    """
    Check if test's errors contain specified exception
    :type test: backslash.test.Test
    :param exception_type: str
    """
    for test_error in test.query_errors():
        if test_error.__dict__['_data']['exception_type'] and \
                test_error.__dict__['_data']['exception_type'].lower() == exception_type.lower():
            return test_error


if __name__ == '__main__':
    baker.run()