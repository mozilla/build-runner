import os

from runner import (
    Config,
    run_task,
    process_taskdir
)

tasksd = os.path.join(os.path.split(__file__)[0], 'test-tasks.d')


def test_tasks_default_config():
    config = Config()
    assert process_taskdir(config, tasksd) is True


def test_max_time():
    t = ['sleep', '10']
    env = {}
    max_time=1
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
