#!/bin/bash
# Copyright (C) 2026 Checkmk GmbH - License: Check_MK Enterprise License
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
#
# Verifies sign_package.sh fails cleanly (nonzero exit, clear message, no
# key/passphrase contents) when the key file is empty or missing, the
# passphrase file points at a missing file, or the imported key doesn't
# match the expected fingerprint.

set -u

SIGN="$1"
OUT="${TEST_TMPDIR}/sign_package_test_out.rpm"
FAKE_FINGERPRINT="0000000000000000000000000000000000000000"

fail() {
    echo "FAIL: $*" >&2
    exit 1
}

out="$("${SIGN}" /dev/null "${OUT}" "" "" "${FAKE_FINGERPRINT}" 2>&1)"
rc=$?
[ "${rc}" -ne 0 ] || fail "expected nonzero exit with an empty key file, got 0: ${out}"
echo "${out}" | grep -q "no signing key file given" ||
    fail "expected 'no signing key file given', got: ${out}"

MISSING_KEY_FILE="/nonexistent/path/to/signing.key"
out="$("${SIGN}" /dev/null "${OUT}" "${MISSING_KEY_FILE}" "" "${FAKE_FINGERPRINT}" 2>&1)"
rc=$?
[ "${rc}" -ne 0 ] || fail "expected nonzero exit with a missing key file, got 0: ${out}"
echo "${out}" | grep -q "Signing key does not exist: ${MISSING_KEY_FILE}" ||
    fail "expected 'Signing key does not exist: ${MISSING_KEY_FILE}', got: ${out}"

# A key that does exist, so the passphrase-file check is reached.
KEY_FILE="/etc/hostname"
MISSING_PASSPHRASE_FILE="/nonexistent/path/to/passphrase"
out="$("${SIGN}" /dev/null "${OUT}" "${KEY_FILE}" "${MISSING_PASSPHRASE_FILE}" "${FAKE_FINGERPRINT}" 2>&1)"
rc=$?
[ "${rc}" -ne 0 ] || fail "expected nonzero exit with a missing passphrase file, got 0: ${out}"
echo "${out}" | grep -q "Passphrase file does not exist: ${MISSING_PASSPHRASE_FILE}" ||
    fail "expected a missing-passphrase-file message, got: ${out}"

if command -v gpg >/dev/null 2>&1 && command -v rpm >/dev/null 2>&1; then
    # A real (unprotected) key, but the wrong expected fingerprint - must
    # be rejected instead of silently signing with whatever key it found.
    GNUPGHOME="$(mktemp -d)"
    export GNUPGHOME
    trap 'rm -rf "${GNUPGHOME}"' EXIT
    chmod 700 "${GNUPGHOME}"
    cat >"${GNUPGHOME}/keygen.batch" <<EOF
%no-protection
Key-Type: RSA
Key-Length: 1024
Name-Real: sign_package_failure_test
Name-Email: test@example.invalid
Expire-Date: 0
%commit
EOF
    gpg --batch --quiet --gen-key "${GNUPGHOME}/keygen.batch" >/dev/null 2>&1
    gpg --batch --export-secret-keys --armor >"${GNUPGHOME}/key.asc" 2>/dev/null

    out="$("${SIGN}" /dev/null "${OUT}" "${GNUPGHOME}/key.asc" "" "${FAKE_FINGERPRINT}" 2>&1)"
    rc=$?
    [ "${rc}" -ne 0 ] || fail "expected nonzero exit on fingerprint mismatch, got 0: ${out}"
    echo "${out}" | grep -q "not found among the secret keys imported" ||
        fail "expected a fingerprint-mismatch message, got: ${out}"
else
    echo "gpg or rpm not installed - skipping the fingerprint-mismatch case" >&2
fi

echo "PASS"
