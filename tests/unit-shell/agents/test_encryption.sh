#!/bin/bash
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

AGENT_LINUX="${UNIT_SH_AGENTS_DIR}/check_mk_agent.linux"

# shellcheck source=agents/check_mk_agent.linux
MK_SOURCE_AGENT="true" source "$AGENT_LINUX"

# mock openssl
openssl() {
    if [ "${1}" = "version" ]; then
        printf "OpenSSL 1.1.1f  31 Mar 2020\n"
    elif [[ " $* " =~ " -pbkdf2 " ]]; then
        # This is the key derivation. We need to output some reasonable values to continue.
        # This is also openssl enc, so this has to live above the encryption case.
        printf "salt=53414C5453414C54\n"
        printf "key=CC00CC00CC00CC00CC00CC00CC00CC00CC00CC00CC00CC00CC00CC00CC00CC00\n"
        printf "iv =11001100110011001100110011001100\n"
    elif [ "${1}" = "enc" ]; then
        # Encryption
        sed 's/plain/cipher/g'
    elif [ "${1}" = "dgst" ]; then
        # Output something that looks like a MAC
        printf "HMACHMACHMACHMACHMACHMACHMACHMAC"
    else
        fail "unexpected openssl command"
    fi
}

test_unencrypted() {
    unset optionally_encrypt

    set_up_encryption

    actual="$(printf "Hello plain 🌍!\n" | optionally_encrypt)"

    assertEquals "Hello plain 🌍!" "${actual}"
}

test_encrypted() {
    unset optionally_encrypt

    ENCRYPTED="yes" set_up_encryption

    expected="$(printf '%s%s%s%s' "05" "SALTSALT" "HMACHMACHMACHMACHMACHMACHMACHMAC" "Hello cipher 🌍!")"
    actual="$(printf "Hello plain 🌍!" | optionally_encrypt)"

    assertEquals "${expected}" "${actual}"
}

test_encryption_does_not_strip_newlines() {
    # Command substitution will remove trailing newlines, so we have to avoid
    # storing intermediate binary computation results in variables.
    #
    # The expected output length is 61 bytes:
    # 2 bytes version, 8 bytes salt, 32 bytes mac, and 19 bytes for the mocked
    # encrypted message "Hello cipher 🌍!\n".
    unset optionally_encrypt

    ENCRYPTED="yes" set_up_encryption

    actual="$(printf "Hello plain 🌍!\n" | optionally_encrypt | wc -c)"

    assertEquals "61" "${actual}"
}

# shellcheck disable=SC1090
. "$UNIT_SH_SHUNIT2"
