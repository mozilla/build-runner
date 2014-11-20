# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

import os
import tempfile
import json

from runner import (
    run_task,
    process_taskdir
)
from runner.lib.config import Config

tasksd = os.path.join(os.path.split(__file__)[0], 'test-tasks.d')


def test_tasks_default_config():
    config = Config()
    assert process_taskdir(config, tasksd) is True


def test_tasks_pre_post_hooks():
    """
    Here we use a hook which will write to a file. We can check the file
    to make sure everything ran smoothly.
    """
    pre_post_hook = os.path.join(os.path.split(__file__)[0], 'pre-post-hook.py')
    logfile = tempfile.mktemp()
    config = Config()

    config.max_time = 1
    config.max_tries = 1
    config.pre_task_hook = "python {} runner-test {}".format(pre_post_hook, logfile)
    config.post_task_hook = "python {} runner-test {}".format(pre_post_hook, logfile)
    process_taskdir(config, tasksd)

    with open(logfile, 'r') as log:
        count = 0
        for line in log:
            count += 1
            log_entry = json.loads(line)
            assert type(log_entry) == dict
            assert type(log_entry.get('task')) == unicode
            assert type(log_entry.get('try_num')) == int
            assert type(log_entry.get('max_retries')) == int
            if count % 2 == 0:
                # every other log line should be from a post_hook and have a
                # result field.
                assert type(log_entry.get('result')) == unicode

    os.remove(logfile)


def test_max_time():
    t = ['sleep', '2']
    env = {}
    max_time = 1
    assert run_task(t, env, max_time) == "RETRY"


def test_task_exit_codes():
    env = {}
    bash_cmd = ['/usr/bin/env', 'bash', '-c']
    success_t = bash_cmd + ['exit 0']
    halt_t = bash_cmd + ['exit 2']
    retry_t = bash_cmd + ['exit 1']

    assert run_task(success_t, env, 1) == "OK"
    assert run_task(halt_t, env, 1) == "HALT"
    assert run_task(retry_t, env, 1) == "RETRY"
