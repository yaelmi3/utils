backslash_url = "https://backslash.infinidat.com/"

session_query_template = 'https://backslash.infinidat.com/rest/sessions?page_size' \
                 '=2000&start_time=gt%3A{}&show_abandoned=false&show_skipped=false'

test_query_template = "https://backslash.infinidat.com/rest/tests?page_size=2000&search=name%" \
             "show_abandoned=false&show_skipped=false&show_successful={1}"

table_style = '<style type="text/css"> .tg  {border-collapse:collapse;border-spacing:0;} ' \
              '.tg td{font-family:Arial, sans-serif;font-size:14px;padding:10px 5px;' \
              'border-style:solid;border-width:1px;overflow:hidden;word-break:normal;' \
              'border-color:black;} .tg th{font-family:Arial, sans-serif;font-size:14px;' \
              'font-weight:normal;padding:10px 5px;border-style:solid;border-width:1px;overflow:' \
              'hidden;word-break:normal;border-color:black;} .tg .tg-yw4l{vertical-align:top}' \
              ' </style> <table class="tg">'

cell_style = '<th class="tg-yw4l">{}</th>'

table_footer = "</table>"