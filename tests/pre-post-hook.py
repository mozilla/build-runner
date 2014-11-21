# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

"""
A simple pre/post hook which writes data to a file
"""
import sys

# protect ourselves from unintentional runs during test discovery
if sys.argv[1] == "runner-test":
    with open(sys.argv[2], 'a') as logfile:
        logfile.write(sys.argv[3])
        logfile.write('\n')
