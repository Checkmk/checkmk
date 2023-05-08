#!/usr/bin/env bash
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

export UNIT_SH_SHUNIT2="./shunit2"
export UNIT_SH_AGENTS_DIR="../agents"
export UNIT_SH_PLUGINS_DIR="$UNIT_SH_AGENTS_DIR/plugins"

_failed_tests=""

run_file() {
    echo -n "Running $1"
    if ! OUTPUT=$("$1"); then
         _failed_tests="$_failed_tests $1"
         echo -e "\n$OUTPUT"
    else
        echo "${OUTPUT##*Ran}" | tr '\n.' ' '
        echo
    fi
}

while IFS= read -r -d '' test_file
do
    run_file "${test_file}"
done <  <(find ./agent-unit -name "test*.sh" -print0)

while IFS= read -r -d '' test_file
do
    run_file "${test_file}"
done <  <(find ./agent-plugin-unit -name "test*.sh" -print0)

if [ -n "$_failed_tests" ]; then
    echo "Failed shell unit tests: $_failed_tests" >&2
    exit 1
fi
