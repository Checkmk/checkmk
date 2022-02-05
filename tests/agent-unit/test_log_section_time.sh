#!/bin/bash
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


AGENT_LINUX="${UNIT_SH_AGENTS_DIR}/check_mk_agent.linux"

# shellcheck source=../../agents/check_mk_agent.linux
MK_SOURCE_AGENT="true" LOG_SECTION_TIME="true" source "$AGENT_LINUX"

oneTimeSetUp() {

    export MK_VARDIR="${SHUNIT_TMPDIR}"
    export MK_LOGDIR="${SHUNIT_TMPDIR}"

    set_up_get_epoch
}

profiling_dir() {
    # there's only one folder (profiling/$DATE_TIME/)...
    echo "${MK_LOGDIR}/profiling/"*
}

wait_for() {
    limit=100
    until [ "${limit}" -eq 0 ] || [ -e "${1}" ]; do
        sleep 0.01
        (( limit-- ))
    done
}

test_basic_function_noop() {
    LOG_SECTION_TIME=false set_up_profiling
    _log_section_time "echo" "whatever" > /dev/null

    assertTrue "[ ! -e $(profiling_dir) ]"
}

test_basic_function() {
    LOG_SECTION_TIME=true set_up_profiling
    _log_section_time "echo" "some" "string" > /dev/null

    assertEquals "
real	0mRUNTIMEs
user	0mRUNTIMEs
sys	0mRUNTIMEs
runtime RUNTIME" "$(sed 's/0[.,][0-9]\+/RUNTIME/' "$(profiling_dir)/echo_some_string_.log")"

}

test_export_with_run_cached() {
    LOG_SECTION_TIME=true set_up_profiling

    run_cached "my_test_name" "42" "_log_section_time" "echo '<<<my_test_section>>>'"

    # wait for the async part to complete
    wait_for "$(profiling_dir)/echo____my_test_section____.log"
    wait_for "${MK_VARDIR}/cache/my_test_name.cache"

    # make sure the file has been created
    assertEquals "<<<my_test_section>>>" "$(cat "${MK_VARDIR}/cache/my_test_name.cache")"
}

# shellcheck disable=SC1090
. "$UNIT_SH_SHUNIT2"
