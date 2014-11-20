# Runner

Runner is a project that manages starting tasks in a defined order. If tasks
fail, the chain can be retried, or halted.

# Configuration

Configuration is done with INI style configuration files.

## [runner] section
Keys:

- `sleep_time`: how long to wait between retries
- `max_tries`: how many times to retry before giving up
- `halt_task`: which task to run to "halt" the process. This could perhaps shut
  the machine down or terminate the EC2 instance
- `pre_task_hook`: a command which will run before each task, with relevant task stats passed in as a json blob.
- `post_task_hook`: a command which will run just after each task, with relevant task stats pass in as a json blob.
- `max_time`: maximum amount of time a task can run
- `interpreter`: an explicit interpreter to be used for running tasks (for platforms which do not support hashbangs).

Task Stats:

pre/post task hooks receive task stats as an argument. Task stats is a json blog of the format:
    {
        "task": "the task name",
        "try_num": "the current try count",
        "max_retries": "passed in via the config",
        "result": "passed only to the post hook, the result of a task run."
    }

## [env] section
Keys and values in this section are passed into tasks as environment variables

## other sections
Configuration for other tasks or purposes can go into their own sections.


# Tasks
Tasks are loaded from a task dir.
Tasks are run as separate processes.

The return code of a task determines what happens next.

Return code 0 means everything went well, and to continue on to the next task.

Return code 2 means to run the "halt" task, and then stop running tasks and exit runner

Other return codes will cause runner to retry tasks from the beginning.

A special environment variable, `"RUNNER_CONFIG_CMD"` is always set in the
environment that allows tasks to easily access configuration. e.g.

    $RUNNER_CONFIG_CMD -g hg.remote

will return the "remote" configuration variable from the "hg" section

# Tests
Tests are run via nose
Run `python setup.py nosetests`, or nose manually

Runner also uses doctests
Run `python -m doctest -v runner.py`
