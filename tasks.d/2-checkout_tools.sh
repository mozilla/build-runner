#!/bin/bash
# Make sure we have tools and mozharness cloned and up-to-date
set -e
HGTOOL=hgtool.py

$HGTOOL /home/catlee/mozilla/tools.hg /tmp/tools
$HGTOOL -b production /home/catlee/mozilla/mozharness /tmp/mozharness
