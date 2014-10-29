#!/usr/bin/env python
"""runner [-v|-q] [-c config] taskdir"""
import os
import re
import time
import subprocess
import copy
import itertools
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
        if self.options.has_option('runner', 'include_dir'):
            # reload the object including files in config.d
            config_dir = self.options.get('runner', 'include_dir')
            configs = [os.path.join(config_dir, c) for c in list_directory(config_dir)]
            if not self.options.read([filename] + configs):
                log.warn("Couldn't load %s", config_dir)
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

    def get_task_config(self, taskname):
        """Returns a dict of the config options for [taskname]
        or an empty dict otherwise
        """
        if self.options is not None and self.options.has_section(taskname):
            return dict(self.options.items(taskname))
        return {}


def list_directory(dirname):
    # List the files in the directory, and sort them
    files = os.listdir(dirname)
    # Filter out files with leading .
    return [f for f in files if f[0] != '.']


def get_task_name(taskfile):
    """
    >>> get_task_name('3-buildbot.py')
    'buildbot'
    >>> get_task_name('buildbot.py')
    'buildbot'
    >>> get_task_name('buildbot')
    'buildbot'
    """
    task_no_prefix = re.search('(^.*-)?(.*)', taskfile).group(2)
    task_no_suffix = ''.join(task_no_prefix.split('.')[0:-1])
    if task_no_suffix == '':
        return taskfile
    return task_no_suffix


class CycleError(Exception):
    pass


class DependencyDoesNotExistError(Exception):
    pass


class TaskGraph(object):
    def __init__(self, taskconfigs):
        self._nodes = {}
        for task in taskconfigs:
            self._nodes[task.name] = task

        self._refresh()

        missing = self._missing_tasks()
        if missing:
            raise DependencyDoesNotExistError("The following are depended on "
                                              "but do not exist: "
                                              + ", ".join(missing))

    def _refresh(self):
        """Refreshes the pointers between graph nodes"""
        for node in self._nodes.values():
            for sd in node.stated_dependencies:
                if sd in self._nodes and sd not in node.dependencies:
                    node.dependencies.add(self._nodes[sd])

    def _missing_tasks(self):
        """List of missing tasks (ie. unfulfilled dependencies)"""
        lst = [node._missing_dependencies() for node in self._nodes.values()]
        return set(itertools.chain.from_iterable(lst))

    def sequential_ordering(self):
        """Topological sort, ignores parallelisation possibilities
        Algorithm is Kahn (1962),
        http://en.wikipedia.org/wiki/Topological_sorting#Algorithms
        """

        to_ret = []
        graph = copy.deepcopy(self._nodes.values())
        no_inc_edges = self._start_nodes(graph)

        while no_inc_edges:
            n = no_inc_edges.pop()
            to_ret.append(n.name)
            for m in self._nodes_with_edges_from(graph, n):
                self._remove_edge(graph, n, m)
                if not set(self._nodes_with_edges_to(graph, m)) - set([n]):
                    no_inc_edges.add(m)

        if self._has_edges(graph):
            # we've got a cycle in our graph!
            raise CycleError("Graph of task dependencies has cycles")

        to_ret.reverse()  # because we point TO our dependents
        return to_ret

    @classmethod
    def _start_nodes(cls, graph):
        """Returns the nodes in the graph with no dependencies"""
        return {n for n in graph
                if not cls._nodes_with_edges_to(graph, n)}

    @staticmethod
    def _has_edges(graph):
        """Returns True if there are any edges remaining in the graph,
        False otherwise"""

        for node in graph:
            if node.dependencies:
                return True
        return False

    @staticmethod
    def _nodes_with_edges_to(graph, n):
        """Returns the list of task nodes which depend on n.

        More generally this means it returns the list of nodes which have
        directed edges pointed to n.
        """
        return {m for m in graph if m is not n and n in m.dependencies}

    @staticmethod
    def _nodes_with_edges_from(graph, n):
        """Returns the list of task nodes which n depends on

        More generally this means it returns the list of nodes which n points
        to
        """
        return copy.copy(n.dependencies)

    @staticmethod
    def _remove_edge(graph, n, m):
        """Remove the edge from n to m"""
        if m not in n.dependencies:
            return

        n.dependencies.remove(m)

    def __str__(self):
        return ", ".join(map(str, self._nodes.values()))


class TaskConfig(object):
    def __init__(self, name, dependencies):
        self.name = name
        self.stated_dependencies = set(dependencies) - set([name])
        self.dependencies = set()

    @classmethod
    def fromtuple(cls, pair):
        return cls(pair[0], pair[1])

    @classmethod
    def fromdict(cls, mapping):
        return cls(mapping['name'], mapping['dependencies'])

    def _missing_dependencies(self):
        return self.stated_dependencies - {d.name for d in self.dependencies}

    def __str__(self):
        return "({}, {}, {})".format(self.name,
                                     self.stated_dependencies,
                                     self.dependencies)


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
        "max_time": config.max_time,
        "max_tries": config.max_tries,
        "sleep_time": config.sleep_time
    }

    for try_num in range(1, config.max_tries + 1):
        for t in task_list:
            # Get the portion of a task's config that can override default_config
            task_config = config.get_task_config(get_task_name(t))
            task_config = {k: int(v) for k, v in task_config.items() if k in default_config}

            # do the override
            for k, v in default_config.items():
                if k not in task_config:
                    task_config[k] = v

            log.debug("%s: starting (max time %is)", t, task_config['max_time'])
            r = run_task(os.path.join(dirname, t), env, max_time=task_config['max_time'])
            log.debug("%s: %s", t, r)

            if r == "OK":
                continue
            elif r == "RETRY":
                # No point in sleeping if we're on our last try
                if try_num == task_config['max_tries']:
                    log.warn("maximum attempts reached")
                    # TODO: halt here too?
                    return False
                # Sleep and try again
                log.debug("sleeping for %i", task_config['sleep_time'])
                time.sleep(task_config['sleep_time'])
                break
            elif r == "HALT":
                # stop/halt/reboot?
                log.info("halting")
                run_task(os.path.join(dirname, config.halt_task), env, max_time=task_config['max_time'])
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
