import tempfile
import os
from flask import Flask
from collections import OrderedDict
from flask import request, render_template, redirect, send_from_directory, current_app

import log
from ui.ui_helper import get_main_inputs, execute_command

app = Flask(__name__)
log.init_log()

app.config['UPLOAD_FOLDER'] = tempfile.gettempdir()


@app.route('/')
def index():
    return render_template('show_entries.html',
                           categories=get_main_inputs())


@app.route('/action/<selected_action>')
def show_menu(selected_action):
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
        return render_template('results.html', html_text=result.html_text, file_name=result.file_name)
    return redirect('/')


@app.route('/uploads/<path:filename>', methods=['GET', 'POST'])
def download(filename):
    return send_from_directory(directory=app.config['UPLOAD_FOLDER'], filename=filename)


if __name__ == '__main__':
    app.run(debug=False, host="0.0.0.0", port=8080, threaded=True)