#!/bin/bash
# Update any shared repos we have
if [ -z "$HG_SHARE_BASE_DIR" ]; then
    echo "HG_SHARE_BASE_DIR not set; exiting"
    exit
fi

echo "Looking for hg repos in $HG_SHARE_BASE_DIR"
# TODO: Update only recent repos? Otherwise we can't clean up old unused ones
for repo in $(find $HG_SHARE_BASE_DIR -type d -name .hg -prune); do
    repo=$(dirname $repo)
    echo "updating $repo"
    hg -R $repo pull
done
