import glob
import random

import click
from slash.frontend.slash_run import slash_run


def get_all_tests_from_suites():
    return [full_path for full_path in
            glob.iglob('suites//**/*.suite',
                       recursive=True)]


def run_random_tests(base_args, num_of_tests):
    tests = []
    for suite in get_all_tests_from_suites():
        for test in open(suite, 'r').readlines():
            if test.startswith('../') and not test.endswith('suite'):
                tests.append(test.rstrip().replace('../', ''))
    if num_of_tests > len(tests):
        selected_tests = tests
    else:
        selected_tests = random.sample(set(tests), num_of_tests)
    base_args.extend(selected_tests)
    nl = '\n'
    print(f'The following tests were selected for execution:{nl}'
          f'{nl.join(str(index + 1) + "." + test for index, test in enumerate(selected_tests))}')
    slash_run(base_args)


@click.command()
@click.option('-l', '--logs')
@click.option('-s', '--system', multiple=True)
@click.option('--num_of_tests', default=10, help="Number of random tests to be executed")
def execute(num_of_tests, logs, system):
    print(f"Running {num_of_tests} random tests on {system}. Logs will be saved under {logs}")
    base_args = ['-vv', '-l', logs, '-s', ''.join(system)]
    run_random_tests(base_args, num_of_tests)


if __name__ == '__main__':
    execute()
