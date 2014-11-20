# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

import os


def list_directory(dirname):
    # List the files in the directory, and sort them
    files = os.listdir(dirname)
    # Filter out files with leading .
    return [f for f in files if f[0] != '.']
