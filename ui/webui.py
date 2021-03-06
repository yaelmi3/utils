import os
from collections import OrderedDict
from pathlib import Path

from flask import Flask
from flask import render_template, redirect, send_from_directory, request, jsonify

import config
import log
from reporting import get_saved_reports, create_tests_table, handle_html_report
from ui.ui_helper import get_main_inputs, execute_command
from processing_tests import get_sorted_tests_list

app = Flask(__name__)
log.init_log()

app.config['UPLOAD_FOLDER'] = config.get_util_dir()


@app.route('/')
def index():
    all_options = get_main_inputs()
    return render_template('show_entries.html',
                           categories=all_options)


@app.route('/action/<selected_action>')
def show_menu(selected_action):
    if selected_action == "coverage_reports":
        html_text = get_saved_reports("coverage_reports")
        return render_template('results.html', html_text=html_text, file_name='')
    categories = get_main_inputs()
    entry = None
    for category_name, category_items in categories.items():
        for command, arguments in category_items.items():
            if command == selected_action:
                entry = categories[category_name][selected_action]

    return render_template('execute.html', selected_action=selected_action,
                           entry=OrderedDict(sorted(entry.items())))


@app.route('/execute', methods=['POST', 'GET'])
def execute():
    if request.method == "POST":
        result = execute_command(request.form)
        if request.form.get('save_static_link'):
            file_name = os.path.basename(result.html)
            return redirect(f'/display_file_link/{file_name}')
        return render_template('results.html', html_text=result.html, file_name=result.file_name)
    return redirect('/')


@app.route('/display_file_link/<file_name>')
def display_file_link(file_name):
    html_text = open(os.path.join(app.config['UPLOAD_FOLDER'], file_name), 'r').read()
    return render_template('results.html', html_text=html_text, file_name='')


@app.route('/uploads/<path:filename>', methods=['GET', 'POST'])
def download(filename):
    return send_from_directory(directory=app.config['UPLOAD_FOLDER'], filename=filename)


@app.route('/get_automerger_errors/<jenkins_job>', methods=['GET', 'POST'])
def get_automerger_errors(jenkins_job):
    failed_tests = get_sorted_tests_list(jenkins_build=f"{config.automerger_path}/{jenkins_job}/",
                                         status=config.failed_statuses)
    html_text = create_tests_table(failed_tests)
    report_path = handle_html_report(html_text, save_as_file=True,
                       message=f"Failed tests for {config.automerger_path}/{jenkins_job}")
    link = f"{request.url_root}display_file_link/" + Path(report_path).name
    failed_tests_for_execution = set(f"{test.test_module}:{test.test_name}" for test in failed_tests)
    return jsonify(link=link, num_of_tests=len(failed_tests), test_list=list(failed_tests_for_execution))


if __name__ == '__main__':
    app.run(debug=False, host="0.0.0.0", port=8080, threaded=True)