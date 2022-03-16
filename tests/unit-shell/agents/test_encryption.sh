#!/bin/bash
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

AGENT_LINUX="${UNIT_SH_AGENTS_DIR}/check_mk_agent.linux"

# shellcheck source=../../agents/check_mk_agent.linux
MK_SOURCE_AGENT="true" source "$AGENT_LINUX"

# mock openssl
openssl() {
    if [ "${1}" = "version" ]; then
        printf "OpenSSL 1.1.1f  31 Mar 2020\n"
    else
        sed 's/plain/cipher/g'
    fi
}

test_unencrypted() {
    unset optionally_encrypt

    set_up_encryption

    actual="$(printf "Hello plain world!\n" | optionally_encrypt)"

    assertEquals "Hello plain world!" "${actual}"
}

test_encrypted() {
    unset optionally_encrypt

    ENCRYPTED="yes"
    set_up_encryption

    actual="$(printf "Hello plain world!" | optionally_encrypt)"

    assertEquals "03Hello cipher world!" "${actual}"
}

test_encryption_does_not_strip_newlines() {
    unset optionally_encrypt

    ENCRYPTED="yes"
    set_up_encryption

    actual="$(printf "Hello plain world!\n" | optionally_encrypt | wc -c)"

    assertEquals "22" "${actual}"
}

# shellcheck disable=SC1090
. "$UNIT_SH_SHUNIT2"
