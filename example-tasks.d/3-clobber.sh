#!/bin/bash
# Clobber any build directories we need to
# TODO: Update clobberer tool to not require branch/builder/builddir/master
TOOLS=$($RUNNER_CONFIG_CMD -g hg.tools_path)
CLOBBER_URL=$($RUNNER_CONFIG_CMD -g buildbot.clobber_url)
slavename=$(hostname -s)

echo python $TOOLS/clobberer/clobberer.py -n ${CLOBBER_URL} idle idle idle $slavename idle
#clobberURL, branch, builder, my_builddir, slave, master
