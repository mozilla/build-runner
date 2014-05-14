#!/bin/bash
# Call purge builds to make sure we have at least 10G free
set -e
TOOLS=$($RUNNER_CONFIG_CMD -g hg.tools_path)
SLAVEDIR=$($RUNNER_CONFIG_CMD -g buildbot.slave_dir)
python $TOOLS/buildfarm/maintenance/purge_builds.py --dry-run -s 10 $SLAVEDIR
