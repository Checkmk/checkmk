#!/usr/bin/env bash
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

export UNIT_SH_SHUNIT2="./shunit2"
export UNIT_SH_PLUGINS_DIR="../agents/plugins"

_failed_tests=""
while IFS= read -r -d '' test_file
do
    echo "--------------------------------------------------------------------------------"
    echo Running "$test_file"
    "$test_file" || _failed_tests="$_failed_tests $test_file"
done <  <(find ./agent-plugin-unit -name "test*.sh" -print0)

if [ -n "$_failed_tests" ]; then
    echo "Failed shell unit tests: $_failed_tests" >&2
    exit 1
fi
