#!/bin/bash
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

set -e -o pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" >/dev/null 2>&1 && pwd)"
# shellcheck source=buildscripts/infrastructure/build-nodes/scripts/build_lib.sh
. "${SCRIPT_DIR}/build_lib.sh"

# read optional command line argument
if [ "$#" -eq 1 ]; then
    PYTHON_VERSION=$1
else
    PYTHON_VERSION=$(get_version "$SCRIPT_DIR" PYTHON_VERSION)
fi

PIPENV_VERSION=$(get_version "$SCRIPT_DIR" PIPENV_VERSION)
VIRTUALENV_VERSION=$(get_version "$SCRIPT_DIR" VIRTUALENV_VERSION)

pip3 install \
    pipenv=="$PIPENV_VERSION" \
    virtualenv=="$VIRTUALENV_VERSION"

# link pipenv to /usr/bin to be in PATH. Fallback to /opt/bin if no permissions for writting to /usr/bin.
#   /opt/bin does not work as default, because `make -C omd deb` requires it to be in /usr/bin.
#   only /usr/bin does not work, because GitHub Actions do not have permissions to write there.
PIPENV_PATH="/opt/Python-${PYTHON_VERSION}/bin/pipenv"
ln -sf "${PIPENV_PATH}"* /usr/bin || ln -sf "${PIPENV_PATH}"* /opt/bin
