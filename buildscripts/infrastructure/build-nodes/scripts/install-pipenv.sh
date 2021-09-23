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
            PYTHON_VERSION=$(make --no-print-directory --file=defines.make print-PYTHON_VERSION)
            break
        elif [ $PWD == / ]; then
            failure "could not determine Python version"
        else
            cd ..
        fi
    done
fi

pip3 install pipenv==2021.5.29 virtualenv==20.7.2

ln -sf "/opt/Python-${PYTHON_VERSION}/bin/pipenv"* /usr/bin

