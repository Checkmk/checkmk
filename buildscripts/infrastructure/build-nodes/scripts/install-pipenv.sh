#!/bin/bash
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

set -e -o pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" >/dev/null 2>&1 && pwd)"
. "${SCRIPT_DIR}/build_lib.sh"

# When building our build containers we don't have the whole repo available,
# but we copy defines.make to scripts (see build-build-containers.jenkins).
# However, in other situations we have the git available and need to find
# defines.make in the repo base directory.
find_defines_make() {
    cd "$SCRIPT_DIR"
    while [ ! -e defines.make ]; do
        if [ "$PWD" = / ] ; then
            failure "could not find defines.make"
            break
        fi
        cd ..
    done
    echo "$PWD/defines.make"
}

get_version() {
    make --no-print-directory --file="$(find_defines_make)" print-"$1"
}

# read optional command line argument
if [ "$#" -eq 1 ]; then
    PYTHON_VERSION=$1
else
    PYTHON_VERSION=$(get_version PYTHON_VERSION)
fi

PIPENV_VERSION=$(get_version PIPENV_VERSION)
VIRTUALENV_VERSION=$(get_version VIRTUALENV_VERSION)

pip3 install \
    pipenv=="$PIPENV_VERSION" \
    virtualenv=="$VIRTUALENV_VERSION"

# link pipenv to /usr/bin to be in PATH. Fallback to /opt/bin if no permissions for writting to /usr/bin.
#   /opt/bin does not work as default, because `make -C omd deb` requires it to be in /usr/bin.
#   only /usr/bin does not work, because GitHub Actions do not have permissions to write there.
PIPENV_PATH="/opt/Python-${PYTHON_VERSION}/bin/pipenv"
ln -sf "${PIPENV_PATH}"* /usr/bin || ln -sf "${PIPENV_PATH}"* /opt/bin
