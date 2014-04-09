# Buildbot Runner

Buildbot runner is a project that manages starting/stopping buildbot
It has a configurable set of plugins that can run as "pre-flight" or "post-flight" tasks

# Configuration
- Need to be able to have common configuration between tasks
  use environment vars?
  json files?
  key/value pairs?
  python module?
  cmdline api?

# pre-flight tasks
Pre-flight tasks run before buildbot is started
If a pre-flight task fails, we can:
* sleep/retry
* halt
* reboot

# post-flight tasks
post-flight tasks run after buildbot finishes
these tasks can do cleanup, and then decide to:
* re-run the loop
* halt
* reboot

# tasks
Tasks are loaded from a task dir, defaults to $PWD/tasks.d
Tasks are run as separate processes.

# sample tasks
- check ami
- check slavealloc
- update (tools, hg-shared, etc.)
- purge builds
- clobber
- kill procs
- run buildbot
- maybe shutdown or reboot
