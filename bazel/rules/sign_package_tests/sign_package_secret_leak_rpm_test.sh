#!/bin/bash
# Copyright (C) 2026 Checkmk GmbH - License: Check_MK Enterprise License
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
#
# Signs a real .rpm with a disposable, sentinel-passphrase-protected key,
# and asserts the sentinel never appears on any subprocess's command line
# (via strace -e trace=execve).
#
# Needs gpg, rpm, rpmbuild and strace on PATH; skips cleanly if unavailable.

set -euo pipefail

SIGN="$1"
SENTINEL="SUPER_SECRET_SENTINEL_3b1c9b0e6a1a4f0c8a2e7d5b6c1f9a3d"

for tool in gpg rpm rpmbuild strace; do
    if ! command -v "${tool}" >/dev/null 2>&1; then
        echo "${tool} not installed - skipping this test" >&2
        exit 0
    fi
done

WORK="$(mktemp -d)"
trap 'rm -rf "${WORK}"' EXIT

GNUPGHOME="${WORK}/gnupghome"
mkdir -p "${GNUPGHOME}"
chmod 700 "${GNUPGHOME}"
export GNUPGHOME

cat >"${WORK}/keygen.batch" <<EOF
Key-Type: RSA
Key-Length: 1024
Name-Real: sign_package_secret_leak_test
Name-Email: test@example.invalid
Expire-Date: 0
Passphrase: ${SENTINEL}
%commit
EOF
gpg --batch --quiet --pinentry-mode loopback --gen-key "${WORK}/keygen.batch" >/dev/null 2>&1

FINGERPRINT="$(
    gpg --batch --with-colons --with-fingerprint --list-secret-keys |
        awk -F: '$1 == "fpr" { print $10; exit }'
)"

printf '%s' "${SENTINEL}" >"${WORK}/passphrase"
gpg --batch --pinentry-mode loopback --passphrase-file "${WORK}/passphrase" \
    --export-secret-keys --armor >"${WORK}/signing.key"
gpg --batch --export --armor "${FINGERPRINT}" >"${WORK}/pub.asc"

mkdir -p "${WORK}/rpmbuild"
cat >"${WORK}/hello.spec" <<'EOF'
Name: hello
Version: 1.0
Release: 1
Summary: sign_package_secret_leak_test fixture
License: MIT
%description
sign_package_secret_leak_test fixture
%files
EOF
rpmbuild --quiet --define "_topdir ${WORK}/rpmbuild" -bb "${WORK}/hello.spec" >/dev/null 2>&1
UNSIGNED_RPM="$(find "${WORK}/rpmbuild/RPMS" -name '*.rpm')"

unset GNUPGHOME

STRACE_LOG="${WORK}/strace.log"
strace -f -e trace=execve -s 10000 -o "${STRACE_LOG}" -- \
    bash "${SIGN}" "${UNSIGNED_RPM}" "${WORK}/signed.rpm" \
    "${WORK}/signing.key" "${WORK}/passphrase" "${FINGERPRINT}"

if grep -qF "${SENTINEL}" "${STRACE_LOG}"; then
    echo "FAIL: sentinel passphrase found on a subprocess command line:" >&2
    grep -F "${SENTINEL}" "${STRACE_LOG}" >&2
    exit 1
fi

# The signing must have actually worked, not merely avoided leaking. Use a
# throwaway --dbpath rather than the host's real rpm database.
RPMDB="${WORK}/rpmdb"
mkdir -p "${RPMDB}"
rpm --dbpath "${RPMDB}" --initdb
rpm --dbpath "${RPMDB}" --import "${WORK}/pub.asc"
if ! rpm --dbpath "${RPMDB}" --checksig "${WORK}/signed.rpm" | grep -q "digests signatures OK"; then
    echo "FAIL: signed.rpm did not verify against the disposable key" >&2
    rpm --dbpath "${RPMDB}" --checksig "${WORK}/signed.rpm" >&2
    exit 1
fi

echo "PASS"
