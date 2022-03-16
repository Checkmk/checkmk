#!/bin/bash
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

TESTEE="${UNIT_SH_AGENTS_DIR}/scripts/super-server/0_systemd/setup"

setUp() {
    # shellcheck source=../../agents/scripts/super-server/0_systemd/setup
    MK_SOURCE_ONLY="true" source "$TESTEE"

    RESOURCES="/systemd-resources"
    ROOT="${SHUNIT_TMPDIR}"
    export RESOURCES ROOT

    mkdir -p "${SHUNIT_TMPDIR}${RESOURCES}"

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

test_systemd_version() {

    systemctl() {
        cat <<HERE
systemd 245 (245.4-4ubuntu3.15)
+PAM +AUDIT +SELINUX +IMA +APPARMOR +SMACK +SYSVINIT +UTMP +LIBCRYPTSETUP +GCRYPT +GNUTLS +ACL +XZ +LZ4 +SECCOMP +BLKID +ELFUTILS +KMOD +IDN2 -IDN +PCRE2 default-hierarchy=hybrid
HERE
    }

    assertEquals "245" "$(_systemd_version)"
}

test_systemd_sufficient_fail_for_219() {
    systemctl() { echo "systemd 219 (foobar)"; }
    _systemd_present() { :; }
    _destination() { :; }

    ERRMSG=$(_systemd_sufficient 2>&1)

    assertFalse "$?"
    assertContains "${ERRMSG}" $'The Checkmk agent may require features that are either buggy,\nor not even supported in systemd versions prior to 220.'
}

test__unit_deployed() {
    _populate_units
    assertTrue "_unit_deployed unit_a"
    assertTrue "_unit_deployed unit_c"
    assertFalse "_unit_deployed unit_x"
}

# shellcheck disable=SC1090
. "$UNIT_SH_SHUNIT2"
