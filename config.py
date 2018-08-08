import sys
from collections import namedtuple
from logbook import Logger, StreamHandler

StreamHandler(sys.stdout).push_application()
log = Logger(__name__)

backslash_url = "https://backslash.infinidat.com/"

session_query_template = 'https://backslash.infinidat.com/rest/sessions?page_size' \
                 '=2000&start_time=gt%3A{}&show_abandoned=false&show_skipped=false'

backslash_test_query_template = "https://backslash.infinidat.com/rest/tests?page_size=2000&search={0}" \
                      "&show_abandoned=false&show_skipped=false&show_successful={1}"

table_style = '<style type="text/css"> .tg  {border-collapse:collapse;border-spacing:0;} ' \
              '.tg td{font-family:Arial, sans-serif;font-size:14px;padding:10px 5px;' \
              'border-style:solid;border-width:1px;overflow:hidden;word-break:normal;' \
              'border-color:black;} .tg th{font-family:Arial, sans-serif;font-size:14px;' \
              'font-weight:normal;padding:10px 5px;border-style:solid;border-width:1px;overflow:' \
              'hidden;word-break:normal;border-color:black;} .tg .tg-yw4l{vertical-align:top}' \
              ' </style> <table class="tg">'

cell_style = '<th class="tg-yw4l">{}</th>'
bold_cell_style = '<th class="tg-yw4l"><b>{}</b></th>'

table_footer = "</table>"

cache_server = namedtuple('cacheserver', ['url', 'port'])( "yaelm-freddy", 6378)

elastic_server_url = 'http://infra-elastic-search:9200/backslash/_search'

default_params = (('size', '2000'),)

headers = {'Content-Type': 'application/json'}

max_error_length = 50

failed_statuses = ["ERROR", "FAILURE"]