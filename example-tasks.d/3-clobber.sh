#!/bin/bash
# Clobber any build directories we need to
# TODO: Update clobberer tool to not require branch/builder/builddir/master
TOOLS=$($RUNNER_CONFIG_CMD -g hg.tools_path)
slavename=$(hostname -s)
python $TOOLS/clobberer/clobberer.py -n http://clobberer.foo.bar idle idle idle $slavename master
