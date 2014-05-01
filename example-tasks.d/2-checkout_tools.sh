#!/bin/bash
# Make sure we have tools and mozharness cloned and up-to-date
set -e
HGTOOL=hgtool.py

TOOLS_REPO=$($RUNNER_CONFIG_CMD -g hg.tools_repo)
TOOLS_BRANCH=$($RUNNER_CONFIG_CMD -g hg.tools_branch)
TOOLS_PATH=$($RUNNER_CONFIG_CMD -g hg.tools_path)
$HGTOOL $TOOLS_REPO -b $TOOLS_BRANCH $TOOLS_PATH

MOZHARNESS_REPO=$($RUNNER_CONFIG_CMD -g hg.mozharness_repo)
MOZHARNESS_BRANCH=$($RUNNER_CONFIG_CMD -g hg.mozharness_branch)
MOZHARNESS_PATH=$($RUNNER_CONFIG_CMD -g hg.mozharness_path)
$HGTOOL $MOZHARNESS_REPO -b $MOZHARNESS_BRANCH $MOZHARNESS_PATH
