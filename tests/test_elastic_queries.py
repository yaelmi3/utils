import pytest

import config
from elastic_search_queries import get_tests_query

TEST_NAME = "my_test"
ERROR_NAME = "my_error"


def test_get_tests_with_unexpected_args():
    """
    Steps:
        Attempt to get query, when one of the arguments is invalid
    Expected:
        Assertion error should be raised
    """
    with pytest.raises(AssertionError):
        get_tests_query(test_name=TEST_NAME, error=ERROR_NAME, bla="bla")
        
        
def test_get_tests_with_error():
    """
    Steps:
        Get failed tests query when both name and errors are provided
    Expected:
        query should contain both test name and query
    """
    query = get_tests_query(test_name=TEST_NAME, error=ERROR_NAME, status=config.failed_statuses)
    assert {'match': {'test.name': TEST_NAME}} in query['query']['bool']['must']
    assert {'terms': {'status': config.failed_statuses}} in query['query']['bool']['must']
    assert {'match': {'errors.message': 'my_error'}} in query['query']['bool']['must']


def test_get_tests_without_error():
    """
    Steps:
        Get failed tests query and provide test name only
    Expected:
        Query should contain the test name, but the error part should not be part of the query
    """
    query = get_tests_query(test_name=TEST_NAME, error=None)
    assert query['query']['bool']['must'][0]['match']['test.name'] == TEST_NAME
    assert 'errors.message' not in query['query']['bool']['must']




