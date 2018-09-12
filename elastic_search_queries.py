import arrow
import requests
from collections import namedtuple

import config
import log


class InternalTest(object):
    def __init__(self, backslash_test, test_params, jira_tickets):
        test_data = backslash_test['_source']
        self._status = test_data['status']
        self._id = test_data["logical_id"]
        self.test_link = config.test_link.format(self._id)
        self.test_name = test_data['test']['name']
        if test_params:
            self.parameters = test_data['parameters']
        self.first_error = _truncate_text(test_data['errors'][0]['message'], 120) if test_data[
            'errors'] else ''
        self.version = test_data['subjects'][0]['version']
        self.start_time = arrow.get(test_data['start_time']).format('DD-MM-YY HH:mm:ss')
        self.duration = arrow.get(
            arrow.get(test_data['end_time'] - test_data['start_time'])).format('HH:mm:ss')
        self.user_name = test_data['user_email'].split('@')[0]
        self.branch = test_data['scm_local_branch'] if test_data['scm_local_branch'] else ''
        self._errors = test_data['errors'] if test_data['errors'] else []
        if jira_tickets:
            self._related_tickets = []
            self.related_tickets = ''


def process_error(error):
    """
    1. Check whether there are errors is test
    2. If errors found, return the first error in the list
    :type error: dict
    :rtype str
    """
    error_message = error['message']
    exception_type = error_message.split(":")[0]
    return _truncate_text(exception_type)


def _truncate_text(exception_type, max_len=config.max_error_length):
    return exception_type if len(exception_type) < config.max_error_length else \
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
                      'error': Query("match", "errors.message"),
                      'days': Query("range", "updated_at"),
                      'status': Query('terms', 'status')
                      }
    tests_query = {"query": {"bool": {"must": []}}}
    for query, query_value in supported_keys.items():
        if query in kwargs and kwargs[query] is not None:
            if query == "days":
                search_value = {"gt": f"now-{kwargs[query]}d"}
            else:
                search_value = kwargs[query]
            tests_query['query']['bool']['must'].append({query_value.operation: {query_value.field: search_value}})
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
        response = requests.post(self.url, params=self.params, headers=self.headers, json=query)
        response.raise_for_status()
        results = response.json()
        log.info(f"Found {results['hits']['total']} results")
        return results['hits']['hits']

    def get_test_results(self, **kwargs):
        """
        1. Get json query
        2. Execute query
        :rtype: dict
        """
        tests_query = get_tests_query(**kwargs)
        log.info(f"Executing query: {tests_query}")
        return self.post_query_request(tests_query)

    def get_errors(self, error_message):
        log.info(f"Executing query for error message = {error_message}")
        erros_query = get_errors_query(error_message)
        return self.post_query_request(erros_query)


