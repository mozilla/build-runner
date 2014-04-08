#!/bin/bash
# Call purge builds to make sure we have at least 10G free
set -e
python /tmp/tools/buildfarm/maintenance/purge_builds.py --dry-run /tmp
