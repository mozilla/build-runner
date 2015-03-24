# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

import os
import sys
import time
import shlex
import json
import random
import subprocess

from lib.config import Config, TaskConfig
from lib.graph import TaskGraph
from lib.utils import list_directory

import logging
log = logging.getLogger(__name__)


def run_task(t, env, max_time):
    start = time.time()
    proc = subprocess.Popen(t, stdin=open(os.devnull, 'r'), env=env)
    while True:
        if proc.poll() is not None:
            break

        if max_time == 0:
            # if we've set to run forever, we can sleep for a lot longer
            # than 1 second.
            time.sleep(20)
        elif time.time() - start > max_time:
            # Try killing it
            log.warn("exceeded max_time; killing")
            proc.terminate()
            return "RETRY"
        else:
            time.sleep(1)

    rv = proc.wait()
    if rv == 0:
        return "OK"
    elif rv == 2:
        return "HALT"
    elif rv == 3:
        return "EXIT"
    else:
        return "RETRY"


def get_task_name(taskfile):
    """
    >>> get_task_name('3-buildbot.py')
    'buildbot'
    >>> get_task_name('buildbot.py')
    'buildbot'
    >>> get_task_name('buildbot')
    'buildbot'
    """
    task_no_prefix = ''.join(taskfile.split('-')[1:])
    taskname = task_no_prefix if task_no_prefix != '' else taskfile

    task_no_suffix = ''.join(taskname.split('.')[0:-1])
    taskname = task_no_suffix if task_no_suffix != '' else taskname

    return taskname


def process_taskdir(config, dirname):
    tasks = list_directory(dirname)
    # Filter out the halting task
    if config.halt_task in tasks:
        tasks.remove(config.halt_task)

    # Get a list of a TaskConfig objects mapping task to their dependencies
    taskconfigs = []
    for t in tasks:
        deps = config.get(get_task_name(t), 'depends_on')
        if deps is not None:
            taskconfigs.append(TaskConfig(t, map(str.strip, deps.split(','))))
        else:
            taskconfigs.append(TaskConfig(t, []))

    tg = TaskGraph(taskconfigs)  # construct the dependency graph
    task_list = tg.sequential_ordering()  # get a topologically sorted order

    log.debug("tasks: %s", task_list)

    env = os.environ.copy()
    new_env = config.get_env()
    log.debug("Updating env with %s", new_env)
    env.update(new_env)

    default_config = {
        "max_time": int(config.max_time),
        "max_tries": int(config.max_tries),
        "sleep_time": int(config.sleep_time),
        "retry_jitter": int(config.retry_jitter),
        "interpreter": config.interpreter,
    }

    start_task = 0  # For starting from the most recent task on a retry.
    for try_num in range(1, config.max_tries + 1):
        for task_count, t in enumerate(task_list[start_task:]):
            # Here we add task_count to start_task to account for the fact that
            # enumerate will start from zero on each loop through, so, if we
            # start from a task other than zero (after a retry) the new offset
            # will be this plus the number of tasks run after.
            start_task = start_task + task_count
            # Get the portion of a task's config that can override default_config
            task_config = config.get_task_config(get_task_name(t))
            task_config_dict = {}
            # do it the long way for < 2.7.5 compatibility
            for k, v in task_config.items():
                if k in default_config:
                    task_config_dict[k] = v
            task_config = task_config_dict

            # do the override
            for k, v in default_config.items():
                if k not in task_config:
                    task_config[k] = v

            # For consistent log info
            task_stats = dict(task=t, try_num=try_num, max_retries=config.max_tries, result="RUNNING")
            if config.task_hook:
                task_hook_cmd = shlex.split("%s '%s'" % (config.task_hook, json.dumps(task_stats)))
                log.debug("running pre-task hook: %s", " ".join(task_hook_cmd))
                run_task(task_hook_cmd, env, max_time=task_config['max_time'])

            log.debug("%s: starting (max time %is)", t, config.max_time)
            task_cmd = os.path.join(dirname, t)
            if task_config['interpreter']:
                log.debug("%s: running with interpreter (%s)", t, task_config['interpreter'])
                # using shlex affords the ability to pass arguments to the
                # interpreter as well (i.e. bash -c)
                task_cmd = shlex.split("%s '%s'" % (task_config['interpreter'], task_cmd))
            r = run_task(task_cmd, env, max_time=task_config['max_time'])
            log.debug("%s: %s", t, r)

            if config.task_hook:
                task_stats['result'] = r
                task_hook_cmd = shlex.split("%s '%s'" % (config.task_hook, json.dumps(task_stats)))
                log.debug("running post-task hook: %s", " ".join(task_hook_cmd))
                run_task(task_hook_cmd, env, max_time=config.max_time)

            halt_cmd = os.path.join(dirname, config.halt_task)
            if config.interpreter:
                # if a global task interpreter was set, it should apply
                # here as well
                halt_cmd = shlex.split("%s '%s'" % (config.interpreter, halt_cmd))

            if r == "OK":
                continue
            elif r == "RETRY":
                # No point in sleeping if we're on our last try
                if try_num == task_config['max_tries']:
                    log.warn("maximum attempts reached")
                    log.info("halting")
                    run_task(halt_cmd, env, max_time=task_config['max_time'])
                    return False
                # Sleep and try again, sleep time is the lower bound within a
                # random jitter. Note: the 1.14 was chosen at random
                # and has no special meaning.
                sleep_time = int((1.14**try_num) * random.randint(
                    task_config['sleep_time'],
                    task_config['sleep_time'] + task_config['retry_jitter']))
                log.debug("sleeping for %i", sleep_time)
                time.sleep(sleep_time)
                break
            elif r == "HALT":
                log.info("halting")
                run_task(halt_cmd, env, max_time=task_config['max_time'])
                return False
            elif r == "EXIT":
                log.info("exiting")
                return False
        else:
            log.debug("all tasks completed!")
            return True


def get_syslog_address():
    # local syslog address depends on platform, and must be set manually in the
    # log handler
    if sys.platform == "linux2":
        return "/dev/log"
    elif sys.platform == "darwin":
        return "/var/run/syslog"
    return


def make_argument_parser():
    import argparse
    parser = argparse.ArgumentParser(__doc__)
    parser.set_defaults(
        loglevel=logging.INFO,
    )
    parser.add_argument("-q", "--quiet", dest="loglevel", action="store_const", const=logging.WARN, help="quiet")
    parser.add_argument("-v", "--verbose", dest="loglevel", action="store_const", const=logging.DEBUG, help="verbose")
    parser.add_argument("-c", "--config", dest="config_file")
    parser.add_argument("-g", "--get", dest="get", help="get configuration value")
    parser.add_argument("-n", "--times", dest="times", type=int, help="run this many times (default is forever)")
    parser.add_argument("-H", "--halt-after", dest="halt_after", action="store_const", const=True,
                        help="Call the halt task after runner finishes (never called if -n is not set).")
    parser.add_argument("--syslog", dest="syslog", action="store_const", const=True, help="send messages to syslog")
    parser.add_argument("--syslog-address", dest="syslog_address", default=get_syslog_address(),
                        help="set a custom syslog address (defaults to system local)")
    parser.add_argument("taskdir", help="task directory", nargs="?")

    return parser


def runner(config, taskdir, times):
    """Runs tasks in the taskdir up to `times` number of times

    times can be None to run forever
    """
    t = 0
    while True:
        t += 1
        if times and t > times:
            break
        log.info("iteration %i", t)
        if not process_taskdir(config, taskdir):
            exit(1)


def main():
    parser = make_argument_parser()
    args = parser.parse_args()

    logging.basicConfig(format="%(asctime)s - %(levelname)s - %(message)s", level=args.loglevel)
    config = Config()

    if args.syslog:
        from logging.handlers import SysLogHandler
        handler = SysLogHandler(address=args.syslog_address)
        log.addHandler(handler)

    if args.config_file:
        config.load_config(args.config_file)

    if args.get:
        log.debug("getting %s", args.get)
        section, option = args.get.split(".", 1)
        v = config.get(section, option)
        if v is not None:
            print v
        exit(0)
    elif not args.taskdir:
        parser.error("taskdir required")

    if not os.path.exists(args.taskdir):
        log.error("%s doesn't exist", args.taskdir)
        exit(1)

    runner(config, args.taskdir, args.times)
    if args.halt_after and config.halt_task:
        halt_cmd = os.path.join(args.taskdir, config.halt_task)
        log.info("finishing run with halt task: %s" % halt_cmd)
        run_task(halt_cmd, os.environ, config.max_time)
