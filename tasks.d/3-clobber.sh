#!/bin/bash
# Clobber any build directories we need to
# TODO: Update clobberer tool to not require branch/builder/builddir/master
slavename=$(hostname -s)
python /tmp/tools/clobberer/clobberer.py -n http://clobberer.foo.bar idle idle idle $slavename master
