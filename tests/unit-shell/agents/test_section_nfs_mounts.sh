#!/bin/bash
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

AGENT_LINUX="${UNIT_SH_AGENTS_DIR}/check_mk_agent.linux"

# shellcheck source=agents/check_mk_agent.linux
MK_SOURCE_AGENT="true" source "$AGENT_LINUX"

fake_proc_mounts() {
    MD=$1
    MP=$2
    if [ -n "${MP}" ]; then
        mkdir "${MP}"
    fi
    cat <<EOF >"${SHUNIT_TMPDIR}/mounts"
${MD/ /\\040} ${MP/ /\\040} nfs rw,relatime,vers=3,rsize=131072,wsize=524288,namlen=255,hard,proto=tcp,timeo=600,retrans=2,sec=sys,mountaddr=10.234.123.10,mountvers=3,mountport=300,mountproto=tcp,local_lock=none,addr=12.234.234.10 0 0
EOF
}

clean_up_fake_proc_mounts() {
    rm -r "$1"
    rm -r "${SHUNIT_TMPDIR}/mounts"
}

fake_waitmax() {
    # shellcheck disable=SC2317 # overwritten function called indirectly
    waitmax() {
        shift 3
        "$@"
    }
}

oneTimeSetUp() {
    fake_waitmax
}

test_section_nfs_mounts_ok() {
    MD="nfs-999-foobar.net:/abc/rs/nfs/yo_checkmk"
    MP="${SHUNIT_TMPDIR}/mountpoint"
    fake_proc_mounts "${MD}" "${MP}"

    section=$(section_nfs_mounts "${SHUNIT_TMPDIR}/mounts")
    nfs=$(echo "${section}" | grep "\{\"mountpoint")
    assertEquals "${MP}" "$(echo "${nfs}" | jq -r '.mountpoint')"
    assertEquals "${MD}" "$(echo "${nfs}" | jq -r '.source')"
    assertEquals "ok" "$(echo "${nfs}" | jq -r '.state')"

    clean_up_fake_proc_mounts "${MP}"
}

test_section_nfs_mounts_not_ok() {
    MD="nfs-999-foobar.net:/abc/rs/nfs/yo_checkmk"
    MP=""
    fake_proc_mounts "${MD}" "${MP}"

    section=$(section_nfs_mounts "${SHUNIT_TMPDIR}/mounts")
    nfs=$(echo "${section}" | grep "\{\"mountpoint")
    assertEquals "${MP}" "$(echo "${nfs}" | jq -r '.mountpoint')"
    assertEquals "${MD}" "$(echo "${nfs}" | jq -r '.source')"
    assertEquals "hanging" "$(echo "${nfs}" | jq -r '.state')"
    assertEquals "0" "$(echo "${nfs}" | jq -r '.usage.total_blocks')"
}

test_section_nfs_mounts_space_in_MP() {
    MD="nfs-999-foobar.net:/abc/rs/nfs/yo_checkmk"
    MP="${SHUNIT_TMPDIR}/ mountpoint"
    fake_proc_mounts "${MD}" "${MP}"

    section=$(section_nfs_mounts "${SHUNIT_TMPDIR}/mounts")
    nfs=$(echo "${section}" | grep "\{\"mountpoint")
    assertEquals "${MP}" "$(echo "${nfs}" | jq -r '.mountpoint')"
    assertEquals "${MD}" "$(echo "${nfs}" | jq -r '.source')"
    assertEquals "ok" "$(echo "${nfs}" | jq -r '.state')"

    clean_up_fake_proc_mounts "${MP}"
}

test_section_nfs_mounts_space_in_MD() {
    MD="nfs-999-foobar.net:/abc/rs/nfs/ checkmk"
    MP="${SHUNIT_TMPDIR}/mountpoint"
    fake_proc_mounts "${MD}" "${MP}"

    section=$(section_nfs_mounts "${SHUNIT_TMPDIR}/mounts")
    nfs=$(echo "${section}" | grep "\{\"mountpoint")
    assertEquals "${MP}" "$(echo "${nfs}" | jq -r '.mountpoint')"
    assertEquals "${MD}" "$(echo "${nfs}" | jq -r '.source')"
    assertEquals "ok" "$(echo "${nfs}" | jq -r '.state')"

    clean_up_fake_proc_mounts "${MP}"
}
# shellcheck disable=SC1090
. "$UNIT_SH_SHUNIT2"
