#!/usr/bin/env bash
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

_REPO="$(git rev-parse --show-toplevel)"

export UNIT_SH_SHUNIT2="${_REPO}/tests/unit-shell/shunit2"
export UNIT_SH_AGENTS_DIR="${_REPO}/agents"
export UNIT_SH_PLUGINS_DIR="$UNIT_SH_AGENTS_DIR/plugins"

_failed_tests=""

run_file() {
    bname="${1##.*tests/unit-shell/}"
    printf "%s" "${bname}"
    if ! OUTPUT=$("${1}"); then
         _failed_tests="$_failed_tests ${bname}"
         printf "\n%s" "${OUTPUT}"
    else
        printf "%s" "${OUTPUT##*Ran}" | tr '\n.' ' '
        printf "\n"
    fi
}

find "${_REPO}/tests/unit-shell" -name "test*.sh"  | while read -r test_file; do
    run_file "${test_file}"
done

if [ -n "$_failed_tests" ]; then
    echo "Failed shell unit tests: $_failed_tests" >&2
    exit 1
fi
