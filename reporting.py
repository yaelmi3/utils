import os
import smtplib
import tempfile
import time
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
import log


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


def handle_html_report(final_html, send_email, message=None):
    if send_email:
        generate_html_report(final_html, send_email, message)
    else:
        save_to_file(f"tests_{time.time()}.html", final_html)
    return final_html


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
    return file_content


def create_tests_table(tests):
    """
    Generate html table as string, using predefined styles
    :type tests: list(backslash.test.Test)
    :rtype: str
    """
    html_text = config.table_style
    if tests:
        cell = config.cell_style
        html_text += f"<tr>{''.join([config.bold_cell_style.format(value.title()) for value in tests[0].__dict__.keys() if not value.startswith('_')])}</tr>"
        for test in tests:
            html_text += "<tr>"
            html_text += ''.join(
                [cell.format(value) for key, value in test.__dict__.items() if not key.startswith('_')])
            html_text += "</tr>"
        html_text += "</table>"
        return html_text
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


def create_test_stats_table(header, test_analysis):
    html_text = f"{config.table_style} <h2>{header}</h2><br>"
    for key, value in test_analysis.items():
        html_text += "<tr>"
        html_text += config.bold_cell_style.format(key)
        html_text += config.cell_style.format(value)
        html_text += "</tr>"
    html_text += "</table>"
    return html_text
