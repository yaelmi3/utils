import os
from flask import Flask
from collections import OrderedDict
from flask import request, render_template, redirect, send_from_directory

import config
import log
from ui.ui_helper import get_main_inputs, execute_command
from reporting import get_saved_reports


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


if __name__ == '__main__':
    app.run(debug=False, host="0.0.0.0", port=8080, threaded=True)