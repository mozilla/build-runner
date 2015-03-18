# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

import os
import tempfile
import json

from nose import with_setup

import runner

from runner.lib.config import Config

tasksd = os.path.join(os.path.split(__file__)[0], 'test-tasks.d')
logfile = tempfile.mktemp()  # this is only a unique name, no file is created


def teardown_logfile():
    # should be used with any test that makes use of the logfile global
    #os.remove(logfile)
    pass


def test_tasks_default_config():
    config = Config()
    assert runner.process_taskdir(config, tasksd) is True


@with_setup(setup=None, teardown=teardown_logfile)
def test_tasks_pre_post_hooks():
    """
    Here we use a hook which will write to a file. We can check the file
    to make sure everything ran smoothly.
    """
    pre_post_hook = os.path.join(os.path.split(__file__)[0], 'pre-post-hook.py')
    config = Config()

    config.max_time = 1
    config.max_tries = 1
    config.retry_jitter = 0
    config.task_hook = "python %s runner-test %s" % (pre_post_hook, logfile)
    runner.process_taskdir(config, tasksd)

    with open(logfile, 'r') as log:
        for count, line in enumerate(log):
            log_entry = json.loads(line)
            assert type(log_entry) == dict
            assert type(log_entry.get('task')) == unicode
            assert type(log_entry.get('try_num')) == int
            assert type(log_entry.get('max_retries')) == int
            assert type(log_entry.get('result')) == unicode


def test_max_time():
    t = ['sleep', '2']
    env = {}
    max_time = 1
    assert runner.run_task(t, env, max_time) == "RETRY"


def test_task_exit_codes():
    env = {}
    bash_cmd = ['/usr/bin/env', 'bash', '-c']
    success_t = bash_cmd + ['exit 0']
    exit_t = bash_cmd + ['exit 3']
    halt_t = bash_cmd + ['exit 2']
    retry_t = bash_cmd + ['exit 1']

    assert runner.run_task(success_t, env, 1) == "OK"
    assert runner.run_task(exit_t, env, 1) == "EXIT"
    assert runner.run_task(halt_t, env, 1) == "HALT"
    assert runner.run_task(retry_t, env, 1) == "RETRY"


original_run_task = None
fake_run_task_return_values = {
    os.path.join(tasksd, '1-say-bar.py'): 'RETRY',
}
fake_run_task_arguments = []  # to spy on what's being passed to run_task


def fake_run_task(*args, **kwargs):
    global fake_run_task_arguments
    fake_run_task_arguments.append((args, kwargs))
    return fake_run_task_return_values.get(args[0], 'OK')


def replace_run_task_with_fake():
    global fake_run_task_arguments
    fake_run_task_arguments = []
    original_run_task = runner.run_task  # noqa
    runner.run_task = fake_run_task


def replace_run_task_with_original():
    runner.run_task = original_run_task


@with_setup(replace_run_task_with_fake, replace_run_task_with_original)
def test_task_retries():
    config = Config()
    config.max_time = 1
    config.max_tries = 2
    config.retry_jitter = 0
    fake_halt_task_name = 'mrrrgns_lil_halt_task'
    config.halt_task = fake_halt_task_name

    return_value = runner.process_taskdir(config, tasksd)
    assert return_value is False
    # 0-say-foo.py + 2x 1-say-bar.py (retry) + halt == 4 calls to run_task
    assert len(fake_run_task_arguments) == 4
    assert fake_run_task_arguments[0][0][0] == os.path.join(tasksd, '0-say-foo.py')
    for offset in (1, 2):
        assert fake_run_task_arguments[offset][0][0] == os.path.join(tasksd, '1-say-bar.py')
    assert fake_run_task_arguments[3][0][0] == os.path.join(tasksd, fake_halt_task_name)


@with_setup(replace_run_task_with_fake, replace_run_task_with_original)
def test_task_exit():
    global fake_run_task_return_values
    fake_run_task_return_values = {
        os.path.join(tasksd, '0-say-foo.py'): 'EXIT',
    }

    config = Config()
    config.max_time = 1
    fake_halt_task_name = 'mrrrgns_lil_halt_task'
    config.halt_task = fake_halt_task_name

    return_value = runner.process_taskdir(config, tasksd)
    assert return_value is False
    # 0-say-foo.py == 1 calls to run_task
    assert len(fake_run_task_arguments) == 1
    assert fake_run_task_arguments[0][0][0] == os.path.join(tasksd, '0-say-foo.py')
