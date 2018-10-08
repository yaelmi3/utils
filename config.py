from collections import namedtuple

backslash_url = "https://backslash.infinidat.com/"

session_query_template = 'https://backslash.infinidat.com/rest/sessions?page_size' \
                 '=2000&start_time=gt%3A{}&show_abandoned=false&show_skipped=false'

backslash_test_query_template = "https://backslash.infinidat.com/rest/tests?page_size=2000&search={0}" \
                      "&show_abandoned=false&show_skipped=false&show_successful={1}"

table_style = '<style type="text/css">table { table-layout:auto;width="100%"} .tg  {border-collapse:collapse;border-spacing:0;} ' \
              '.tg td{word-wrap: break-word, overflow: hidden;text-overflow: ellipsis; font-family:Arial, sans-serif;font-size:14px;padding:10px 5px;' \
              'border-style:solid;border-width:5px;overflow:hidden;word-break:normal;' \
              'border-color:black;} .tg th{font-family:Arial, sans-serif;font-size:14px;' \
              'font-weight:normal;padding:10px 5px;border-style:solid;border-width:1px;overflow:' \
              'hidden;word-break:normal;border-color:black;} .tg .tg-yw4l{vertical-align:top}' \
              ' </style> <table class="tg">'

log_name = "utils.log"

cache_server_up = True


def get_cache_state():
    global cache_server_up
    return cache_server_up


def set_cache_state(state):
    """
    Updates current cache server per session
    :type state: bool
    """
    global cache_server_up
    cache_server_up = state


cell_style = '<th class="tg-yw4l">{}</th>'
bold_cell_style = '<th class="tg-yw4l"><b>{}</b></th>'

table_footer = "</table>"

cache_server = namedtuple('cacheserver', ['url', 'port'])( "yaelm-freddy.lab.gdc.il.infinidat.com", 6378)

elastic_server_url = 'http://infra-elastic-search:9200/backslash/_search'

page_scroll_format = "?scroll={}m"

default_params = (('size', '10000'),)

headers = {'Content-Type': 'application/json'}

max_error_length = 50

failed_statuses = ["ERROR", "FAILURE"]

all_statuses = ["SUCCESS"] + failed_statuses

from_address = "ymintz@infinidat.com"

smtp_server = 'smtp-dev.lab.il.infinidat.com'

ignore_branches = ["/", "cli"]

omit_errors = ["KeyboardInterrupt", 'bdb.BdbQuit', 'TEST_INTERRUPTED',
               'sherlock_client.exc.ResourceLocked']

generic_errors = ["AssertionError"]

jira_query = 'updated > -365d' \
             ' and resolution not in (Duplicate,  "Not a Bug", "Idea Rejected")' \
             ' and (text ~ "{0}")' \
             ' and (project = "Infinibox Tests" or' \
             ' project = InfiniBox or project = "Infrastructure Development")'

jira_link = '<a href="https://jira.infinidat.com/browse/{0}">{0}</a>'
jira_link_status = '<a href="https://jira.infinidat.com/browse/{0}">{0} - {1}</a>'

test_link = '<a href="https://backslash.infinidat.com/#/tests/{0}">{0}</a>'

tests_search_link = '<a href="https://backslash.infinidat.com/#/tests?search={0}">{0}</a>'

webui_menus_index = {"Queries": ["obtain_all_test_errors", "test_stats", "get_failed_tests_by_name", "find_test_by_error"],
                     "Reports": ["coverage_by_version", "suites_overview", "show_jira_blockers", "find_tests_by_name_in_repo"]}

webui_ignore_vararg_list = ["send_email"]


max_tests_to_keep = 100
definite_executions_threshold = 10

