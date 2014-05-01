#!/usr/bin/env python
"""runner [-v|-q] [-c config] taskdir"""
import os
import time
import subprocess
import re
import sys
from ConfigParser import RawConfigParser

import logging
log = logging.getLogger(__name__)


def run_task(t, env, max_time):
    start = time.time()
    proc = subprocess.Popen(t, stdin=open(os.devnull, 'r'), env=env)
    while True:
        if proc.poll() is not None:
            break

        if time.time() - start > max_time:
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
    else:
        return "RETRY"


class Config(object):
    sleep_time = 1
    max_tries = 5
    max_time = 600
    halt_task = "halt.sh"
    filename = None
    options = None

    def load_config(self, filename):
        self.filename = filename
        self.options = RawConfigParser()
        # The default optionxform converts option names to lower case. We want
        # to preserve case, so change the transform function to just return the
        # str value
        self.options.optionxform = str
        if not self.options.read([filename]):
            log.warn("Couldn't load %s", filename)
            self.options = None
            return

        if self.options.has_option('runner', 'sleep_time'):
            self.sleep_time = self.options.getint('runner', 'sleep_time')
        if self.options.has_option('runner', 'max_tries'):
            self.max_tries = self.options.getint('runner', 'max_tries')
        if self.options.has_option('runner', 'max_time'):
            self.max_time = self.options.getint('runner', 'max_time')
        if self.options.has_option('runner', 'halt_task'):
            self.halt_task = self.options.get('runner', 'halt_task')

    def get(self, section, option):
        if self.options and self.options.has_option(section, option):
            return self.options.get(section, option)
        return None

    def get_env(self):
        retval = {}
        if self.options and self.options.has_section('env'):
            for option, value in self.options.items('env'):
                retval[str(option)] = str(value)
        if self.filename:
            retval['RUNNER_CONFIG_CMD'] = '{python} {runner} -c {configfile}'.format(
                python=sys.executable,
                runner=os.path.abspath(sys.argv[0]),
                configfile=os.path.abspath(self.filename),
            )
        return retval


def maybe_int(x):
    """Returns int(x), or x if x can't be converted to an int"""
    try:
        return int(x)
    except ValueError:
        return x


def naturalsort_key(x):
    """
    Splits x into numbers/not-numbers so it can be sorted
    """
    return [maybe_int(y) for y in re.split("(\d+)", x)]


def process_taskdir(config, dirname):
    # List the files in the directory, and sort them
    tasks = sorted(os.listdir(dirname), key=naturalsort_key)
    # Filter out files with leading .
    tasks = [t for t in tasks if t[0] != '.']
    # Filter out the halting task
    if config.halt_task in tasks:
        tasks.remove(config.halt_task)

    log.debug("tasks: %s", tasks)

    env = os.environ.copy()
    new_env = config.get_env()
    log.debug("Updating env with %s", new_env)
    env.update(new_env)

    max_time = config.max_time

    for try_num in range(1, config.max_tries + 1):
        for t in tasks:
            log.debug("%s: starting (max time %is)", t, max_time)
            r = run_task(os.path.join(dirname, t), env, max_time=max_time)
            log.debug("%s: %s", t, r)
            if r == "OK":
                continue
            elif r == "RETRY":
                # No point in sleeping if we're on our last try
                if try_num == config.max_tries:
                    log.warn("maximum attempts reached")
                    # TODO: halt here too?
                    return False
                # Sleep and try again
                log.debug("sleeping for %i", config.sleep_time)
                time.sleep(config.sleep_time)
                break
            elif r == "HALT":
                # stop/halt/reboot?
                log.info("halting")
                run_task(os.path.join(dirname, config.halt_task), env, max_time=max_time)
                return False
        else:
            log.debug("all tasks completed!")
            return True


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
    parser.add_argument("taskdir", help="task directory", nargs="?")

    return parser


def runner(config, taskdir, times):
    """Runs tasks in the taskdir up to `times` number of times

    times can be None to run forever
    """
    t = 0
    while True:
        t += 1
        log.info("iteration %i", t)
        if times and t > times:
            break
        if not process_taskdir(config, taskdir):
            exit(1)


def main():
    parser = make_argument_parser()
    args = parser.parse_args()
    logging.basicConfig(format="%(asctime)s - %(levelname)s - %(message)s", level=args.loglevel)

    config = Config()
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


if __name__ == '__main__':
    main()
