import pathlib
import smtplib
import time
import socket
from email import encoders
from email.encoders import encode_base64
from email.mime.base import MIMEBase
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.utils import COMMASPACE

import dominate
from bs4 import BeautifulSoup
from dominate import tags

import config
import graphs
import log
from cache_client import update_cache, get_from_cache


def generate_html_report(html, recipients, message):

    current_time = time.strftime('%d/%m/%Y')
    if not message:
        message = f"Daily test results for {current_time}"
        subject = f"Execution Results {current_time}"
    else:
        subject = message
    with dominate.document(title='Test Report') as doc:
        tags.html(tags.h2("Greetings,"))
        tags.html(tags.h3(f"{message} (attached)"))
    doc = str(doc)
    send_mail(send_to=recipients, subject=subject,
              message=doc, payload=html)
    return html


def send_html_report(doc, payload, subject, recipient_list):
    """
    Create message container - the correct MIME type is multipart/alternative.
    Record the MIME types of both parts - text/plain and text/html.
    Send the message via local SMTP server.
    sendmail function takes 3 arguments: sender smtp_session address, recipient smtp_session address
    and message to send - here it is sent as one string.
    :type doc: str
    :type payload: str
    :type subject: str
    :type recipient_list: list
    """
    msg = MIMEMultipart('alternative')
    msg['Subject'] = subject
    msg['From'] = config.from_address
    recipients = recipient_list
    msg['To'] = ', '.join(recipients)
    part = MIMEBase('application', "octet-stream")
    part.set_payload(payload)
    part2 = MIMEText(str(doc), 'html')
    encode_base64(part)
    part.add_header('Content-Disposition', 'attachment; filename="text.html"')
    msg.attach(part)

    smtp_session = smtplib.SMTP('smtp-dev.lab.il.infinidat.com')
    log.notice("Sending summary report to the following recipients: {0}".format(recipients))
    smtp_session.sendmail(config.from_address, recipients, msg.as_string())
    smtp_session.quit()


def send_mail(send_to, subject, message, payload, use_tls=True):
    """
    Compose and send email with provided info and attachments.
    :type send_to: list
    :type subject: str
    :type message: str
    :type payload: str
    :type use_tls: bool
    """
    msg = MIMEMultipart()
    msg['From'] = config.from_address
    msg['To'] = COMMASPACE.join(send_to)
    msg['Subject'] = subject
    msg.attach(MIMEText(message, 'html'))
    part = MIMEBase('application', "octet-stream")
    part.set_payload(payload)
    encoders.encode_base64(part)
    part.add_header('Content-Disposition',
                    'attachment; filename="{}"'.format(f"tests_{time.time()}.html"))
    msg.attach(part)
    smtp = smtplib.SMTP(config.smtp_server)
    if use_tls:
        smtp.starttls()
    smtp.sendmail(config.from_address, send_to, msg.as_string())
    smtp.quit()


def table_of_contents(html):
    """
    Analyze thr given html file and add table of contents, based on specified tags in the html
    :type html: str
    :rtype: str
    """
    soup = BeautifulSoup(html, "lxml")
    toc = []
    current_list = toc
    previous_tag = None
    for header in soup.findAll(['h2', 'h3']):
        if 'tag' in header.attrs:
            header['id'] = header.attrs['tag']
            if previous_tag == 'h2' and header.name == 'h3':
                current_list = []
            elif previous_tag == 'h3' and header.name == 'h2':
                toc.append(current_list)
                current_list = toc
            header_content = header.string if header.string else header.a
            current_list.append((header['id'], header_content))
            previous_tag = header.name
    if current_list != toc:
        toc.append(current_list)
    return "<h2> Table of Contents </h2> " + _list_to_html(toc) + html


def _list_to_html(lst):
    result = ["<ul>"]
    for item in lst:
        if isinstance(item, list):
            result.append(_list_to_html(item))
        else:
            result.append('<li><a href="#%s">%s</a></li>' % item)
    result.append("</ul>")
    return " ".join(result)


def _get_table_headers(tests):
    headers = ''.join([config.bold_cell_style.format(value.title())
                       for value in tests[0].__dict__.keys()
                       if not value.startswith('_')])
    return f"<tr>{headers}</tr>"


def handle_html_report(final_html, **kwargs):
    """
    Supported kwargs: send_email, save_as_file, message, save_to_redis, file_name
    :type final_html: str
    :rtype: str
    """
    redis_key = kwargs.get("save_to_redis")

    if kwargs.get("send_email"):
        generate_html_report(final_html, kwargs.get("send_email"), kwargs.get("message"))
    if kwargs.get("save_as_file"):
        saved_file_path = save_to_file(final_html,
                                       kwargs.get("file_name", f"tests_{time.time()}.html"))
        if redis_key:
            update_cache(redis_key, str(saved_file_path))
        return str(saved_file_path)
    return final_html


def save_to_file(file_content, file_name=None):
    """
    Save given data to specified path and notify about file creation
    :type file_name: str
    :type file_content: str
    """
    file_path = pathlib.Path(config.get_util_dir()) / file_name if file_name else pathlib.Path(
        config.get_util_dir()) / f"tests_{time.time()}.html"
    with open(file_path, 'w') as file_handle:
        file_handle.write(file_content)
        log.notice(f"File was created at: {file_path}")
    return file_path


def create_tests_table(tests, header=''):
    """
    Generate html table as string, using predefined styles
    :type tests: list(backslash.test.Test)
    :type header: str
    :rtype: str
    """
    index = 0
    html_text = config.table_style
    if tests:
        cell = config.cell_style
        for index, test in enumerate(tests):
            if index == 0:
                html_text += f"<tr>{''.join([config.bold_cell_style.format(value.title()) for value in test.__dict__.keys() if not value.startswith('_')])}</tr>"
            html_text += "<tr>"
            html_text += ''.join(
                [cell.format(value) for key, value in test.__dict__.items() if not key.startswith('_')])
            html_text += "</tr>"
        html_text += "</table>"
        header += f"<b> {index + 1} tests</b><br>"
        return header + html_text
    log.error("Could not find tests that match the query")
    return ''


def create_errors_table(test_and_errors, updated_failed_tests):
    html_text = ''
    for error_name, tests in test_and_errors.items():
        error_name_str = error_name.replace("<",'')
        html_text += f"<h3 id={error_name_str} tag={error_name_str}>{error_name_str}</h3>"
        html_text = f"{html_text}{create_tests_table(tests)} <br>"
    return f'<h2>{len(updated_failed_tests)} failed tests were found</h2><br>' + table_of_contents(
        html_text)


def create_suites_table(tests_by_suites):
    html_text = f"{config.table_style} <h2>Tests grouped by suites</h2><br>"
    html_text += graphs.create_graph_bar({key_name: len(members) for key_name, members in tests_by_suites.items()})
    for suite_name, test_list in tests_by_suites.items():
        html_text += f"<h3 id={suite_name} tag={suite_name}>{suite_name} ({len(test_list)})</h3>"
        html_text += f"<table class='tg'> {''.join(['<tr>' + config.cell_style.format(test) + '</tr>' for test in test_list])}"
        html_text += "</table>"
    return table_of_contents(html_text)


def create_tests_list(test_list, header):
    html_text = f"{config.table_style} <h2>{header}</h2><br>"
    html_text += f"<table class='tg'> {''.join(['<tr>' + config.cell_style.format(test) + '</tr>' for test in test_list])}"
    html_text += "</table>"
    return html_text


def create_test_stats_table(header, test_analysis, note):
    html_text = f"{config.table_style} <h2>{header}</h2><br>"
    if note:
        html_text += f'<font color="red">*** {note}</font>'
    for key, value in test_analysis.items():
        html_text += "<tr>"
        html_text += config.bold_cell_style.format(key.replace('_', ' ').title())
        html_text += config.cell_style.format(value)
        html_text += "</tr>"
    html_text += "</table> <br>"
    return html_text


def create_test_blockers_table(test_blockers):
    html_text = f"<h2>Test Blockers - {sum(len(blockers) for blockers in test_blockers.values())}</h2><br>"
    html_text += graphs.create_graph_bar({key_name: len(members) for key_name, members in test_blockers.items()})
    for blocker_status, blocked_tests in test_blockers.items():
        html_text += f"<h3 id={blocker_status} tag={blocker_status}>{blocker_status} ({len(blocked_tests)})</h3>"
        html_text +=  f"{config.table_style}"
        html_text += f"<tr>{''.join([config.bold_cell_style.format(value.title()) for value in blocked_tests[0].keys() if not value.startswith('_')])}" \
                     f"</tr>"
        for test in blocked_tests:
            html_text += "<tr>"
            html_text += ''.join(
                [config.cell_style.format(value) for _, value in test.items()])
            html_text += "</tr>"
        html_text += "</table>"
    return table_of_contents(html_text)


def create_coverage_report(header, coverage_data, errors):
    html_text = f"<h2>{header}</h2><br>"
    html_text += f"<h3 id=coverage tag=coverage>" \
                 f"Coverage: {calculate_coverage(coverage_data)}%</h3>"
    html_text += graphs.create_pie_chart(
        labels=[label_name.title() for label_name in coverage_data.keys()],
        values=[len(values) for values in coverage_data.values()])

    html_text += f"<h3 id=errors_ratio tag=errors_ratio>Total Errors</h3>"
    html_text += graphs.create_2_columns_table(["Error Name", "Occurrences"], errors)

    for key_name in ["flaky", "Last_10_SUCCESS", "Last_10_ERROR"]:
        if coverage_data[key_name]:
            html_text += f"<h3 id={key_name} tests tag={key_name} tests>{key_name.title()}</h3>"
            updated_tests = _adjust_tests_to_table(coverage_data, key_name)
            html_text += graphs.create_generic_table(["Test Name", "Success", "Failure"],
                                              [sub_data for sub_data in updated_tests],
                                              len(updated_tests[0]))

    for key_name in ['not_executed', 'blocked']:
        if coverage_data[key_name]:
            html_text += f"<h3 id={key_name} tests tag={key_name} tests>{key_name.title()}</h3>"
            html_text += graphs.create_generic_table(["Test Name"], [coverage_data[key_name]], len(coverage_data[key_name]))

    for key_name in ["SUCCESS", "ERROR"]:
        if coverage_data[key_name]:
            html_text += f"<h3 id={key_name} tests tag={key_name} tests>{key_name.title()}</h3>"
            html_text += graphs.create_2_columns_table(["Test Name", "Occurrences"],
                                                {test_name: len(tests) for test_name, tests in
                                                 coverage_data[key_name].items()})

    return table_of_contents(html_text)


def _adjust_tests_to_table(coverage_data, key_name):
    return [[full_test.split(":")[1] for full_test in coverage_data[key_name].keys()]] +\
                          [[status["SUCCESS"] for status in coverage_data[key_name].values()]] +\
                          [[status["FAILURE"] for status in coverage_data[key_name].values()]]


def calculate_coverage(coverage_data):
    total = sum([len(values) for _, values in coverage_data.items()])
    executed = sum([len(values) for key_name, values in coverage_data.items() if
                    key_name != "not_executed" and key_name != "blocked"])
    return int(executed/total * 100)


def get_saved_reports(key_name):
    """
    1. Get reports location from cache by specified key name
    2. Go through the list and remove all file location that are not found
    3. Sort files byb version and then by days ascending
    :type key_name: str
    :rtype: str
    """
    list_of_report_paths = get_from_cache(key_name)

    if list_of_report_paths:
        reports_by_ver = _get_reports_from_cache(list_of_report_paths)
        html_text = "<h2 Coverage Reports </h2>"
        for version, reports in reports_by_ver.items():
            html_text += f"<h3 id={version} tests tag={version} tests>{version.title().replace('_', '.')}</h3>"
            for report in reports:
                html_text += f'<a href="http://{socket.getfqdn()}:8080/display_file_link/{report}">{report}</a>'
        return table_of_contents(html_text)


def _get_reports_from_cache(list_of_report_paths):
    reports_by_ver = {}
    valid_reports = [pathlib.Path(report_path).name for report_path in list_of_report_paths if
                     pathlib.Path(report_path).exists()]

    for report in valid_reports:
        version = report.split("__")[0]
        if version in reports_by_ver:
            reports_by_ver[version].append(report)
        else:
            reports_by_ver[version] = [report]
    return reports_by_ver
