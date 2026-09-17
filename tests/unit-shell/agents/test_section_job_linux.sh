#!/bin/bash
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

AGENT_LINUX="${UNIT_SH_AGENTS_DIR}/check_mk_agent.linux"

# shellcheck source=agents/check_mk_agent.linux
MK_SOURCE_AGENT="true" source "$AGENT_LINUX"

# section_job() copied the content of every job file into the agent output verbatim, so a
# user who could write a file below ${MK_VARDIR}/job/<user>/ decided what the agent reports.
# CMK-38538 fixed that: the agent now escapes the markers below while reading a job file.
#
# The agent parser knows four marker forms, and job file content reaches all of them. Each
# has its own effect, measured against cmk.checkengine.parser.AgentParser:
#
#   <<<uptime>>>           opens a section: everything up to the next marker is parsed as
#                          uptime data for this host.
#   <<<>>>                 section footer: the rest of the job section is dropped, so every
#                          job the agent emits after this one - i.e. other users' jobs -
#                          disappears from monitoring.
#   <<<<victim-host>>>>    piggyback header: the rest of the job section is dropped *and*
#                          every following section (uptime, df, ...) is taken away from this
#                          host and delivered as victim-host's monitoring data.
#   <<<<>>>>               piggyback footer: truncates like <<<>>>.
#
# and, one level down, the job section's own record separator:
#
#   ==> payroll <==        starts a new job entry, so one file can impersonate any job.
#
# The two empty-name forms are the ones an escaping rule is most likely to miss, which is
# why they get their own tests rather than being folded into the named ones.
assert_marker_not_emitted() {
    marker="$1"
    output="$2"

    assertEquals "job file content reached the agent output as a marker line" \
        "" "$(printf '%s\n' "${output}" | grep -xF "${marker}")"
}

oneTimeSetUp() {
    # find -user in section_job() matches the directory name against a real account, so the
    # job directory has to be named after the user running the test - which is also the
    # attacker's position: a user writing into their own job directory.
    # A container without a passwd entry for the build user has no name to match; find
    # accepts a numeric UID just as well.
    JOB_USER="$(id -un 2>/dev/null || id -u)"
}

setUp() {
    JOBDIR="${SHUNIT_TMPDIR}/job"
    rm -rf "${JOBDIR}"
    mkdir -p "${JOBDIR}/${JOB_USER}"
}

section_job_with_injected_line() {
    printf 'start_time 1547301201\n%s\nexit_code 0\n' "$1" >"${JOBDIR}/${JOB_USER}/backup"

    section_job
}

test_job_file_is_reported_below_its_own_header() {

    printf 'start_time 1547301201\nexit_code 0\n' >"${JOBDIR}/${JOB_USER}/backup"

    output="$(section_job)"

    assertEquals "<<<job>>>
==> backup <==
start_time 1547301201
exit_code 0" "${output}"
}

test_injected_section_header_does_not_open_a_new_section() {

    output="$(section_job_with_injected_line "<<<uptime>>>")"

    assert_marker_not_emitted "<<<uptime>>>" "${output}"
}

test_injected_section_footer_does_not_truncate_the_job_section() {

    output="$(section_job_with_injected_line "<<<>>>")"

    assert_marker_not_emitted "<<<>>>" "${output}"
}

test_injected_piggyback_header_does_not_divert_the_agent_output() {

    output="$(section_job_with_injected_line "<<<<victim-host>>>>")"

    assert_marker_not_emitted "<<<<victim-host>>>>" "${output}"
}

test_injected_piggyback_footer_does_not_truncate_the_job_section() {

    output="$(section_job_with_injected_line "<<<<>>>>")"

    assert_marker_not_emitted "<<<<>>>>" "${output}"
}

test_injected_job_header_does_not_create_a_second_job() {

    output="$(section_job_with_injected_line "==> payroll <==")"

    assert_marker_not_emitted "==> payroll <==" "${output}"
}

test_job_header_indented_by_the_attacker_does_not_create_a_second_job() {

    output="$(section_job_with_injected_line "   ==> payroll <==")"

    assertEquals "job file content reached the agent output as a job header" \
        "" "$(printf '%s\n' "${output}" | grep -E '^[[:space:]]*==> payroll <==$')"
}

test_sanitizing_does_not_cost_the_job_its_own_data() {

    output="$(section_job_with_injected_line "<<<uptime>>>")"

    assertEquals "start_time 1547301201
exit_code 0" "$(printf '%s\n' "${output}" | grep -E '^(start_time|exit_code)')"
}

# shellcheck disable=SC1090
. "$UNIT_SH_SHUNIT2"
