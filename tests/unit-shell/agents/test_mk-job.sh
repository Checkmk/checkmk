#!/bin/bash
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# shellcheck source=agents/check_mk_agent.linux

test_cleanup_old_jobs() {
    MK_SOURCE_ONLY="true" source "${UNIT_SH_AGENTS_DIR}/mk-job"

    # arange
    jobdir="$(mktemp -d)"

    # lets create some job that needs to be cleaned up, because the process
    # name/command does not contain mk-job
    touch "$jobdir/something.1running"
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

# shellcheck disable=SC1090
. "$UNIT_SH_SHUNIT2"
