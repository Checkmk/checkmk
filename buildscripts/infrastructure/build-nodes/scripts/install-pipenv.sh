#!/bin/bash
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

set -e -o pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" >/dev/null 2>&1 && pwd)"
. "${SCRIPT_DIR}/build_lib.sh"

# read optional command line argument
if [ "$#" -eq 1 ]; then
    PYTHON_VERSION=$1
else
    cd "${SCRIPT_DIR}"
    while true; do
        if [ -e defines.make ]; then
            PYTHON_VERSION=$(make -f defines.make print-PYTHON_VERSION)
            break
        elif [ $PWD == / ]; then
            failure "could not determine Python version"
        else
            cd ..
        fi
    done
fi

PYTHON_DIR_NAME=Python-${PYTHON_VERSION}

PIPENV_VERSION=2020.11.15
ARCHIVE_NAME=v${PIPENV_VERSION}.tar.gz
DIR_NAME=pipenv-${PIPENV_VERSION}
TARGET_DIR=/opt

cd "${TARGET_DIR}"
mirrored_download "${ARCHIVE_NAME}" "https://github.com/pypa/pipenv/archive/${ARCHIVE_NAME}"
tar xf "${ARCHIVE_NAME}"
cd "${DIR_NAME}"
pip3 install .

ln -sf "${TARGET_DIR}/${PYTHON_DIR_NAME}/bin/pipenv"* /usr/bin
