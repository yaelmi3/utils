from flask import Flask
from collections import OrderedDict
from flask import request, render_template

import log
from ui.ui_helper import get_main_inputs, execute_command

app = Flask(__name__)
log.init_log()


@app.route('/')
def index():
    return render_template('show_entries.html',
                           categories=get_main_inputs())


@app.route('/action/<selected_action>')
def show_post(selected_action):
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
    result = execute_command(request.form)
    return render_template('results.html', article=result)


if __name__ == '__main__':
    app.run(debug=False, host="0.0.0.0", port=8080, threaded=True)