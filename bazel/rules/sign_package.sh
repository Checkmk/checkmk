#!/bin/bash
# Copyright (C) 2026 Checkmk GmbH - License: Check_MK Enterprise License
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
#
# Signs an .rpm (rpm --resign) with a GPG key file and (optional) passphrase
# file, both passed as arguments - never read from environment variables,
# and never declared as Bazel inputs. See bazel/rules/sign_package.md.

set -euo pipefail

usage() {
    echo "usage: $0 <src> <out> <key_file> <passphrase_file> <expected_fingerprint>" >&2
    exit 1
}

[ "$#" -eq 5 ] || usage

SRC="$1"
OUT="$2"
KEY_FILE="$3"
PASSPHRASE_FILE="$4"
EXPECTED_FINGERPRINT="$5"

GPG_BIN="$(command -v gpg)" || {
    echo "gpg is not installed" >&2
    exit 1
}

if [ -z "${KEY_FILE}" ]; then
    echo "no signing key file given" >&2
    exit 1
fi
if [ ! -f "${KEY_FILE}" ]; then
    echo "Signing key does not exist: ${KEY_FILE}" >&2
    exit 1
fi

if [ -n "${PASSPHRASE_FILE}" ] && [ ! -f "${PASSPHRASE_FILE}" ]; then
    echo "Passphrase file does not exist: ${PASSPHRASE_FILE}" >&2
    exit 1
fi

case "${OUT}" in
    *.rpm) ;;
    *)
        echo "don't know how to sign ${OUT} (expected .rpm)" >&2
        exit 1
        ;;
esac
command -v rpm >/dev/null || {
    echo "rpm is not installed" >&2
    exit 1
}
# rpm --resign execs this as a separate process; on EL it's the independently
# installable rpm-sign package, unlike rpm-build.
command -v rpmsign >/dev/null || {
    echo "rpmsign is not installed" >&2
    exit 1
}

# Ephemeral keyring - never $HOME/.gnupg or the Bazel tree - removed on exit.
GNUPGHOME="$(mktemp -d)"
trap 'rm -rf "${GNUPGHOME}"' EXIT
chmod 700 "${GNUPGHOME}"
export GNUPGHOME

# gpg never prints secret material on import, so show its stderr on
# failure instead of swallowing the only clue why a key was rejected.
if ! IMPORT_OUTPUT="$("${GPG_BIN}" --batch --import "${KEY_FILE}" 2>&1 >/dev/null)"; then
    echo "Failed to import ${KEY_FILE}: ${IMPORT_OUTPUT}" >&2
    exit 1
fi

# Look up the expected fingerprint directly and sign with it specifically,
# rather than trusting whatever import order gpg would otherwise pick.
if ! "${GPG_BIN}" --batch --with-colons --list-secret-keys "${EXPECTED_FINGERPRINT}" >/dev/null 2>&1; then
    echo "expected_fingerprint (${EXPECTED_FINGERPRINT}) not found among" \
        "the secret keys imported from ${KEY_FILE}" >&2
    exit 1
fi
KEY_ID="${EXPECTED_FINGERPRINT}"

cp "${SRC}" "${OUT}"
chmod u+w "${OUT}"

GPG_SIGN_BIN="${GPG_BIN}"
EXTRA_ARGS="--batch"
if [ -n "${PASSPHRASE_FILE}" ]; then
    # rpm builds gpg's argv itself, so the passphrase can't go through
    # %_gpg_sign_cmd_extra_args. Wrap %__gpg instead; only a fixed env var
    # *name* is substituted here, never the path itself, so an unusual path
    # can't break the generated script.
    export SIGN_PACKAGE_PASSPHRASE_FILE="${PASSPHRASE_FILE}"
    GPG_SIGN_BIN="${GNUPGHOME}/gpg-passphrase-wrapper.sh"
    cat >"${GPG_SIGN_BIN}" <<WRAPPER
#!/bin/sh
exec "${GPG_BIN}" --pinentry-mode loopback --passphrase-file "\${SIGN_PACKAGE_PASSPHRASE_FILE}" "\$@"
WRAPPER
    chmod u+x "${GPG_SIGN_BIN}"
    EXTRA_ARGS="--batch --passphrase-repeat=0"
fi
rpm \
    -D "%_signature gpg" \
    -D "%_gpg_path ${GNUPGHOME}" \
    -D "%_gpg_name ${KEY_ID}" \
    -D "%__gpg ${GPG_SIGN_BIN}" \
    -D "%_gpg_sign_cmd_extra_args ${EXTRA_ARGS}" \
    --resign "${OUT}"

# --resign exits 0 even when it signs nothing, so confirm our key's
# signature actually landed. Read it straight off the rpm header instead of
# importing the key into an rpm keyring to check it: that import step isn't
# portable across rpm/gpg versions, unlike this basic header query.
SIG_INFO="$(rpm -qp --qf '%{RSAHEADER:pgpsig}%{DSAHEADER:pgpsig}' "${OUT}" 2>/dev/null)"
case "$(printf '%s' "${SIG_INFO}" | tr '[:upper:]' '[:lower:]')" in
    *"$(printf '%s' "${KEY_ID: -16}" | tr '[:upper:]' '[:lower:]')"*) ;;
    *)
        echo "no signature from ${KEY_ID} found after signing: ${SIG_INFO:-(none)}" >&2
        exit 1
        ;;
esac
