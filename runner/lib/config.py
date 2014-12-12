# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

import os
import sys

from ConfigParser import RawConfigParser
from .utils import list_directory

import logging
log = logging.getLogger(__name__)


class Config(object):
    sleep_time = 1
    max_tries = 5
    max_time = 600
    halt_task = "halt.sh"
    task_hook = None
    interpreter = None
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
        if self.options.has_option('runner', 'task_hook'):
            self.task_hook = self.options.get('runner', 'task_hook')
        if self.options.has_option('runner', 'interpreter'):
            self.interpreter = self.options.get('runner', 'interpreter')

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
