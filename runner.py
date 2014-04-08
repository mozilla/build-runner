#!/usr/bin/env python
"""runner [-v|-q] [-c config] taskdir"""
import os
import time
import subprocess
import re

import logging
log = logging.getLogger(__name__)


def run_task(t):
    proc = subprocess.Popen(t, stdin=open(os.devnull, 'r'))
    rv = proc.wait()
    if rv == 0:
        return "OK"
    elif rv == 2:
        return "HALT"
    else:
        return "RETRY"


class config:
    sleep_time = 1
    max_tries = 5
    halt_task = "halt.sh"


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


def process_taskdir(dirname):
    # List the files in the directory, and sort them
    tasks = sorted(os.listdir(dirname), key=naturalsort_key)
    # Filter out files with leading .
    tasks = [t for t in tasks if t[0] != '.']
    # Filter out the halting task
    if config.halt_task in tasks:
        tasks.remove(config.halt_task)

    log.debug("tasks: %s", tasks)

    for try_num in range(1, config.max_tries + 1):
        for t in tasks:
            log.debug("%s: starting", t)
            r = run_task(os.path.join(dirname, t))
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
                run_task(os.path.join(dirname, config.halt_task))
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
    parser.add_argument("-c", "--config", dest="config")
    parser.add_argument("-n", "--times", dest="times", type=int, help="run this many times (default is forever)")
    parser.add_argument("taskdir", help="task directory")

    return parser


def main():
    parser = make_argument_parser()
    args = parser.parse_args()
    logging.basicConfig(format="%(asctime)s - %(levelname)s - %(message)s", level=args.loglevel)

    # TODO: Load the config

    if not os.path.exists(args.taskdir):
        log.error("%s doesn't exist", args.taskdir)
        exit(1)

    t = 0
    while True:
        t += 1
        log.info("iteration %i", t)
        if args.times and t > args.times:
            break
        if not process_taskdir(args.taskdir):
            exit(1)


if __name__ == '__main__':
    main()
