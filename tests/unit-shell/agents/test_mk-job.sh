#!/bin/bash
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# shellcheck source=agents/check_mk_agent.linux

test_cleanup_old_jobs() {
    MK_SOURCE_ONLY="true" source "${UNIT_SH_AGENTS_DIR}/mk-job"

    # arange
    jobdir="$(mktemp -d)"

    # a running process whose command does not contain mk-job — should be cleaned up
    sleep 9999 &
    bg_pid=$!
    touch "$jobdir/something.${bg_pid}running"
    # this one is no longer running (we don't know the name then, so we don't
    # have to fake it):
    touch "$jobdir/something.$(bash -c 'echo $$')running"
    # and one that should stay
    # (this is actually a crude hack: we use this process, the name contains
    # 'mk-job' so cleanup_running_files thinks it should not be cleaned up)
    touch "$jobdir/something.$$running"

    # just make sure we have created three different files:
    assertEquals "3" "$(find "$jobdir" -type f | wc -l)"

    cleanup_running_files "$jobdir" "something"
    kill "$bg_pid" 2>/dev/null

    # assert
    assertEquals "1" "$(find "$jobdir" -type f | wc -l)"
    expected="something\.$$running"
    assertTrue "ls -1 $jobdir | grep $expected"

    # cleanup
    rm -r "$jobdir"
}

test_cleanup_old_jobs_empty_folder() {
    MK_SOURCE_ONLY="true" source "${UNIT_SH_AGENTS_DIR}/mk-job"

    jobdir="$(mktemp -d)"
    cleanup_running_files "$jobdir" "something"

    rm -r "$jobdir"
}

_mk_job_sandbox() {
    # isolated MK_VARDIR/TMPDIR and a bin dir to shadow commands in
    sandbox="$(mktemp -d)"
    mkdir -p "${sandbox}/bin" "${sandbox}/vardir" "${sandbox}/tmp"
}

_hide_command() {
    # make ${1} behave like it is not installed
    printf '#!/bin/sh\nexit 127\n' >"${sandbox}/bin/${1}"
    chmod +x "${sandbox}/bin/${1}"
}

_run_mk_job() {
    # main() ends in 'exit', so it has to run in a subshell
    (
        PATH="${sandbox}/bin:${PATH}"
        MK_VARDIR="${sandbox}/vardir"
        TMPDIR="${sandbox}/tmp"
        MK_SOURCE_ONLY="true" source "${UNIT_SH_AGENTS_DIR}/mk-job" "$@"
        main "$@"
    ) >/dev/null 2>&1
}

_assert_start_time_is_parsable() {
    # The <<<job>>> parser only evaluates lines that consist of exactly two
    # fields. A 'start_time' without a value is therefore dropped silently and
    # the check plug-in crashes with a KeyError much later (CMK-20768).
    job_file="$(find "${sandbox}/vardir/job" -type f -name "${1}")"
    assertNotEquals "no job output file written" "" "${job_file}"
    assertEquals "start_time must consist of key and value" \
        "2" "$(awk '/^start_time/ {print NF}' "${job_file}")"
    assertTrue "start_time must be an epoch timestamp" \
        "grep -qE '^start_time [0-9]+\$' '${job_file}'"
}

test_start_time_is_written() {
    _mk_job_sandbox

    _run_mk_job "MyJob" /bin/echo "hello"

    _assert_start_time_is_parsable "MyJob"
    rm -r "${sandbox}"
}

test_start_time_is_written_without_perl() {
    _mk_job_sandbox
    _hide_command "perl"

    _run_mk_job "MyJob" /bin/echo "hello"

    _assert_start_time_is_parsable "MyJob"
    rm -r "${sandbox}"
}

# shellcheck disable=SC1090
. "$UNIT_SH_SHUNIT2"
