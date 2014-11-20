# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

import os

from runner import (
    run_task,
    process_taskdir
)
from runner.lib.config import Config


def test_tasks_default_config():
    config = Config()
    tasksd = os.path.join(os.path.split(__file__)[0], 'test-tasks.d')
    assert process_taskdir(config, tasksd) is True


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
