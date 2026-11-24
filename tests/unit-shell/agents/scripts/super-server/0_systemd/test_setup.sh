#!/bin/bash
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

TESTEE="${UNIT_SH_AGENTS_DIR}/scripts/super-server/0_systemd/setup"

setUp() {
    # shellcheck source=agents/scripts/super-server/0_systemd/setup
    MK_SOURCE_ONLY="true" source "$TESTEE"

    RESOURCES="/systemd-resources"
    ROOT="${SHUNIT_TMPDIR}"
    export RESOURCES ROOT

    mkdir -p "${SHUNIT_TMPDIR}${RESOURCES}"

}

tearDown() {
    rm -f "${SHUNIT_TMPDIR}${RESOURCES}"/*
}

_populate_units() {
    mkdir -p "${SHUNIT_TMPDIR}/usr/lib/systemd/system"
    touch "${SHUNIT_TMPDIR}/usr/lib/systemd/system/unit_a"
    touch "${SHUNIT_TMPDIR}/usr/lib/systemd/system/unit_b"
    mkdir -p "${SHUNIT_TMPDIR}/lib/systemd/system"
    touch "${SHUNIT_TMPDIR}/lib/systemd/system/unit_c"
    touch "${SHUNIT_TMPDIR}/lib/systemd/system/unit_d"
    touch "${SHUNIT_TMPDIR}/lib/systemd/system/unit_e"
}

test_destination_fail() {
    ERRMSG="$(_destination 2>&1)"

    assertFalse $?
    assertContains "${ERRMSG}" "Unable to figure out where to put the systemd units"
}

test_destination_ok() {
    _populate_units
    assertEquals "/lib/systemd/system" "$(_destination)"
    assertEquals $'/lib/systemd/system\n/usr/lib/systemd/system' "$(_destination --all)"

}

# shellcheck disable=SC2317 # overwritten function called indirectly
test_systemd_version() {

    systemctl() {
        cat <<HERE
systemd 245 (245.4-4ubuntu3.15)
+PAM +AUDIT +SELINUX +IMA +APPARMOR +SMACK +SYSVINIT +UTMP +LIBCRYPTSETUP +GCRYPT +GNUTLS +ACL +XZ +LZ4 +SECCOMP +BLKID +ELFUTILS +KMOD +IDN2 -IDN +PCRE2 default-hierarchy=hybrid
HERE
    }

    assertEquals "245" "$(_systemd_version)"
}

# shellcheck disable=SC2317 # overwritten function called indirectly
test_systemd_sufficient_fail_for_218() {
    systemctl() { echo "systemd 218 (foobar)"; }
    _systemd_present() { :; }
    _destination() { :; }

    ERRMSG=$(_systemd_sufficient 2>&1)

    assertFalse "$?"
    assertContains "${ERRMSG}" $'The Checkmk agent may require features that are either buggy,\nor not even supported in systemd versions prior to 220.'
}

# shellcheck disable=SC2317 # overwritten function called indirectly
test_deploy_fail_for_219() {
    systemctl() { echo "systemd 219 (foobar)"; }
    _systemd_present() { :; }
    _destination() { :; }
    _deploy_controller() { false; }
    _deploy_systemd_units() { :; }

    ERRMSG=$(deploy 2>&1)

    assertFalse "$?"
    assertContains "${ERRMSG}" $'The Checkmk agent may need to know the IP address of the querying site.'
}

# shellcheck disable=SC2317 # overwritten function called indirectly
test_deploy_ok_for_219() {
    systemctl() { echo "systemd 219 (foobar)"; }
    _systemd_present() { :; }
    _destination() { :; }
    _deploy_controller() { true; }
    _deploy_systemd_units() { :; }

    deploy 2>&1
    assertTrue "$?"
}

test__unit_deployed() {
    _populate_units
    assertTrue "_unit_deployed unit_a"
    assertTrue "_unit_deployed unit_c"
    assertFalse "_unit_deployed unit_x"
}

_deploy_unit() {
    # $1 = unit, $2 = content of the packaged unit file
    printf "%s\n" "${2}" >"${SHUNIT_TMPDIR}${RESOURCES}/${1}"
    mkdir -p "${SHUNIT_TMPDIR}/usr/lib/systemd/system"
    touch "${SHUNIT_TMPDIR}/usr/lib/systemd/system/${1}"
}

# shellcheck disable=SC2317 # overwritten function called indirectly
test_cleanup_deactivates_unit_while_its_unit_file_exists() {
    # CMK-40902 AC3, AC4
    _deploy_unit "cmk-update-agent.timer" "[Install]"
    CONTROLLER_TARGET="${SHUNIT_TMPDIR}/cmk-agent-ctl"
    _systemd_present() { :; }
    systemctl() {
        [ -e "${SHUNIT_TMPDIR}/usr/lib/systemd/system/${2}" ] && echo "${1} ${2}" >>"${SHUNIT_TMPDIR}/deactivated"
    }

    cleanup >/dev/null

    assertEquals $'disable cmk-update-agent.timer\nstop cmk-update-agent.timer' "$(sort "${SHUNIT_TMPDIR}/deactivated")"
    assertFalse "[ -e ${SHUNIT_TMPDIR}/usr/lib/systemd/system/cmk-update-agent.timer ]"
}

# shellcheck disable=SC2317 # overwritten function called indirectly
test_cleanup_keeps_unit_without_install_section_running() {
    _deploy_unit "cmk-agent-ctl-installer@.service" "[Service]"
    CONTROLLER_TARGET="${SHUNIT_TMPDIR}/cmk-agent-ctl"
    _systemd_present() { :; }
    systemctl() { echo "${1} ${2}" >>"${SHUNIT_TMPDIR}/stopped_installer"; }

    cleanup >/dev/null

    assertFalse "[ -e ${SHUNIT_TMPDIR}/stopped_installer ]"
    assertFalse "[ -e ${SHUNIT_TMPDIR}/usr/lib/systemd/system/cmk-agent-ctl-installer@.service ]"
}

# shellcheck disable=SC1090
. "$UNIT_SH_SHUNIT2"
