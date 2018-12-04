import ast
from collections import namedtuple

import arrow
import requests

import config
import log
from jira_queries import get_jira_tickets


class InternalTest(object):
    def __init__(self, backslash_test, test_params, jira_tickets):
        test_data = backslash_test['_source']
        self._status = test_data['status']
        self._id = test_data["logical_id"]
        self.test_link = config.test_link.format(self._id)
        self.test_name = test_data['test']['name']
        self.test_module = test_data['test']['file_name']
        self.parameters = _get_test_params(test_params, test_data)
        self.first_error = _truncate_text(test_data['errors'][0]['message'], 120) if test_data[
            'errors'] else ''
        self.version = test_data['subjects'][0]['version']
        self.system = test_data['subjects'][0]['name']
        self.start_time = arrow.get(test_data['start_time']).format('DD-MM-YY HH:mm:ss')
        self.duration = arrow.get(
            arrow.get(test_data['end_time'] - test_data['start_time'])).format('HH:mm:ss')
        self._duration = test_data['end_time'] - test_data['start_time']
        self.user_name = test_data['user_email'].split('@')[0]
        self.branch = test_data['scm_local_branch'] if test_data['scm_local_branch'] else ''
        self._errors = test_data['errors'] if test_data['errors'] else []
        if jira_tickets:
            self._related_tickets = []
            self.related_tickets = ''
            get_jira_tickets(self)


def _get_test_params(test_params, test_data):
    if test_params and test_data['parameters'] and test_data['parameters'] != 'null':
        params_dict = ast.literal_eval(
            test_data['parameters'].replace('true', 'True').replace('false', 'False').replace(
                'null', 'None'))
        return {key: str(value) for key, value in params_dict.items()}


def process_error(error, max_length=config.max_error_length):
    """
    1. Check whether there are errors is test
    2. If errors found, return the first error in the list
    :type error: dict
    :rtype str
    """
    error_message = error['message']
    exception_type = error_message.split(":")[0]
    display_error = exception_type.split('.')[-1]
    return _truncate_text(display_error, max_length)


def _truncate_text(exception_type, max_len):
    return exception_type if len(exception_type) < max_len else \
        f"{exception_type[0:max_len]}..."


def get_tests_query(**kwargs):
    """
    1. Validate input,  only the following var names are allowed: test_name, error, days_delta, status
    1. Combine query based on given test name and error
    2. If error is not provided, remove the error sequence from the query dict
    :rtype: dict
    """
    Query = namedtuple('Query', 'operation field')
    supported_keys = {"test_name": Query("match", "test.name"),
                      'error': Query("match_phrase", "errors.message"),
                      'days': Query("range", "updated_at"),
                      'status': Query('terms', 'status'),
                      'version': Query('prefix', "subjects.version")
                      }
    tests_query = {"query":
        {"bool":
            {
                "must": [
                    {"prefix": {"test.name": {"value": "test_"}}},
                ],
                "must_not": [
                    {"query_string": {
                        "default_field": "errors.message",
                        "query": "KeyboardInterrupt OR bdb.BdbQuit"}},
                    {"range": {"num_interruptions": {"gte": 1}}},
                ]}},
        "sort": [{"_id": "desc"}, {"start_time": "asc"}]}

    for query, query_value in supported_keys.items():
        if query in kwargs and kwargs[query] is not None:
            if query == "days":
                search_value = {"gt": f"now-{kwargs[query]}d"}
            else:
                search_value = kwargs[query]
            tests_query['query']['bool']['must'].append(
                {query_value.operation: {query_value.field: search_value}})
    if kwargs.get("include_simulator") is False:
        tests_query['query']['bool']['must_not'].append({"match": {"subjects.name": "simulator_1"}})
    if kwargs.get('coverage'):
        #tests_query['query']['bool']['must_not'].append({"match": {"subjects.version": "dev"}})
        tests_query['query']['bool']['must'].append({"match": {"session_metadata.Project": "infinibox_tests"}})
        tests_query['query']['bool']['must_not'].append({"prefix": {"test.file_name": "tests/test_utils_tests"}})
    return tests_query


def get_errors_query(error_message):
    """
    :type error_message: str
    :rtype: dict
    """
    return {"query": {"bool": {"must": [{"match": {"errors.message": error_message}},
                                        {"terms": {"status": ["ERROR", "FAILURE"]}},
                                        ]}}}


class ElasticSearch(object):
    def __init__(self):
        self.url = config.elastic_server_url
        self.params = config.default_params
        self.headers = config.headers

    def post_query_request(self, query):
        results = self._post_request(self.url, query)
        total_results = results['hits']['total']

        log.info(f"Found {total_results} results")
        returned_results = results['hits']['hits']
        if total_results > len(returned_results):
            self._search_after_query(query, returned_results, total_results)
        return returned_results

    def _search_after_query(self, query, returned_results, total_results):
        query["search_after"] = returned_results[-1]["sort"]
        while len(returned_results) < total_results:
            results = self._post_request(self.url, query)
            new_results = results['hits']['hits']
            returned_results.extend(new_results)
            query["search_after"] = new_results[-1]["sort"]
            log.info(f"{len(returned_results)} out of {total_results}")


    def _scroll_pages(self, total_results, returned_results, query):
        num_of_scrolls = total_results // len(returned_results)
        if total_results % len(returned_results):
            num_of_scrolls += 1
        log.info(f"Number of results requires {num_of_scrolls} scrolls")
        for scroll_num in range(2, num_of_scrolls):
            scroll_url = f"{self.url}{config.page_scroll_format.format(scroll_num)}"
            log.info(f"Scrolling to {scroll_url}")
            results = self._post_request(scroll_url, query)
            returned_results.append(results['hits']['hits'])

    def _post_request(self, url, query):
        log.info(f"Executing query: {query}")
        response = requests.post(url, params=self.params, headers=self.headers, json=query)
        response.raise_for_status()
        return response.json()

    def get_test_results(self, **kwargs):
        """
        1. Get json query
        2. Execute query
        :rtype: dict
        """
        tests_query = get_tests_query(**kwargs)
        return self.post_query_request(tests_query)

    def get_errors(self, error_message):
        log.info(f"Executing query for error message = {error_message}")
        erros_query = get_errors_query(error_message)
        return self.post_query_request(erros_query)


