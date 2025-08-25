#!/usr/bin/env bash
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# Example invocations:
# tests/unit-shell/runner.sh test_bourne_shell.sh
# tests/unit-shell/runner.sh tests/unit-shell/agents/test_bourne_shell.sh
# tests/unit-shell/runner.sh

UNIT_SH_REPO_PATH="$(git rev-parse --show-toplevel)"
UNIT_SH_SHUNIT2="${UNIT_SH_REPO_PATH}/tests/unit-shell/shunit2"
UNIT_SH_AGENTS_DIR="${UNIT_SH_REPO_PATH}/agents"
UNIT_SH_PLUGINS_DIR="${UNIT_SH_AGENTS_DIR}/plugins"

find_test_files() {
    PATTERN="$(basename "${1:-test_*.sh}")"
    # watch out! make sure a failure is reflected in the exit code
    find "${UNIT_SH_REPO_PATH}/tests/unit-shell" -name "${PATTERN}"
}

run_file() {
    bname="${1##.*tests/unit-shell/}"
    printf "%s\n" "${bname}"
    if ! OUTPUT=$("${1}"); then
        _failed_tests="$_failed_tests ${bname}"
        printf "\n%s\n" "${OUTPUT}"
        return 1
    fi

    printf "%s" "${OUTPUT##*Ran}" | tr '\n.' ' '
    printf "\n"
    return 0
}

run_files() {
    RETCODE=0
    while read -r test_file; do
        run_file "${test_file}" || RETCODE="$?"
    done

    [ -n "$_failed_tests" ] && echo "Failed shell unit tests: $_failed_tests" >&2
    return "${RETCODE}"
}

main() {
    export UNIT_SH_REPO_PATH UNIT_SH_SHUNIT2 UNIT_SH_AGENTS_DIR UNIT_SH_PLUGINS_DIR

    # watch out! make sure a failure is reflected in the exit code
    find_test_files "$@" | run_files
}

[ -z "${MK_SOURCE_ONLY}" ] && main "$@"
