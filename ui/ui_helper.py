from ast import literal_eval
from collections import OrderedDict, namedtuple

import config
import utils


class Fields(object):
    def __init__(self, name, **kwargs):
        self.name = name
        self.default = kwargs.get('default')
        self.field_type = 'text'
        self.fields = None
        self.required = False
        self.update_kwargs(kwargs)
        self.type = None
        self.define_field_types()

    def define_field_types(self):
        if isinstance(self.default, bool):
            self.type = 'checkbox'
            self.default = not self.default
        elif isinstance(self.default, list):
            self.field_type = self.type = 'select'
            self.fields = [Fields(name=field_name) for field_name in self.default]
        else:
            self.type = self.field_type
            self.fields = self.fields
            self.default = self.default

    def update_kwargs(self, kwargs):
        for kwarg_name, kwarg_value in kwargs.items():
            if hasattr(self, kwarg_name):
                setattr(self, kwarg_name, kwarg_value)

    def __repr__(self):
        return '{}: {}'.format(self.name, self.default)


def get_main_inputs():
    all_commands = OrderedDict()
    for menu_name in config.webui_menus_index:
        all_commands.update({menu_name: {}})
    baker_commands = obtain_util_commands()
    for func_name, arguments in baker_commands.items():
        menu_name = _get_menu_name(func_name)
        if menu_name:
            all_commands[menu_name][func_name] = get_list_of_args(arguments)
    return all_commands


def _get_menu_name(func_name):
    """
    Return menu name from dict by specified func name
    :type func_name: str
    :rtype: str
    """
    for menu_name, funcs in config.webui_menus_index.items():
        if func_name in funcs:
            return menu_name

def get_list_of_args(arguments):
    list_of_fields = {'arguments': []}
    default = ''
    for arg in arguments.argnames:
        if arg in arguments.keywords and arguments.keywords[arg] is not None:
            default = arguments.keywords[arg]
        fields = Fields(name=arg, default=default)
        if arg not in arguments.keywords:
            fields.required = True
        list_of_fields['arguments'].append(fields)
    if arguments.has_varargs:
        fields = Fields(name=arguments.varargs_name)
        list_of_fields['arguments'].append(fields)
    return list_of_fields


def obtain_util_commands():
    return {command: arguments for command, arguments in utils.baker._baker.commands.items()}


def execute_command(request_form):
    function_name = {v: k for k, v in request_form.items()}.get('Submit')
    function_arguments = utils.baker._baker.commands[function_name]
    args = get_args(function_arguments, request_form.to_dict())
    if hasattr(utils, function_name):
        result = getattr(utils, function_name)(*args.arguments, *args.vargs)
        return result


def get_args(function_arguments, form_input):
    Args = namedtuple('Args', 'arguments vargs')
    args = Args([], [])
    for argument_name in function_arguments.argnames:
        if argument_name in form_input:
            args.arguments.append(_eval_input(form_input.get(argument_name)))
        else:
            # In case the argument is not in the function argnames, it means its value is False and
            # and while it isn't listed in the form, we still need to pass it with it's arg, in this
            # case as False
            args.arguments.append(False)
    if function_arguments.has_varargs:
        varargs = _eval_input(form_input.get(function_arguments.varargs_name))
        if varargs is not None:
            args.vargs.append(varargs)
    return args


def _eval_input(input_value):
    if input_value == '':
        return None
    try:
        return literal_eval(input_value)
    except (ValueError, SyntaxError):
        return input_value
