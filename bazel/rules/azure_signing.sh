#!/usr/bin/env bash
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# Authenticode signing via Azure Artifact Signing with psign, and verification
# of each signature and its RFC 3161 timestamp. Sourced by sign_azure.sh and
# sign_tar_azure.sh.
#
# Environment:
#   AZURE_ARTIFACT_SIGNING_ENDPOINT, _ACCOUNT, _PROFILE
#   AZURE_ARTIFACT_SIGNING_TENANT_ID, _CLIENT_ID, _CLIENT_SECRET
#   AZURE_ARTIFACT_SIGNING_CORRELATION_ID
#
# No secret is passed on a command line: psign reads the service principal from
# AZURE_* env vars, and the metadata file with the CorrelationId lives in the
# caller's 0700 work dir.

AZURE_SIGNING_VARS=(
    AZURE_ARTIFACT_SIGNING_ENDPOINT
    AZURE_ARTIFACT_SIGNING_ACCOUNT
    AZURE_ARTIFACT_SIGNING_PROFILE
    AZURE_ARTIFACT_SIGNING_TENANT_ID
    AZURE_ARTIFACT_SIGNING_CLIENT_ID
    AZURE_ARTIFACT_SIGNING_CLIENT_SECRET
    AZURE_ARTIFACT_SIGNING_CORRELATION_ID
)

TSA_URL="http://timestamp.acs.microsoft.com"
# Start of the subject of the certificate Artifact Signing issues for our profile.
EXPECTED_SIGNER="CN=Checkmk GmbH,O=Checkmk GmbH,"

# The timestamp server fails a request now and then, and a build signs several
# files. psign only replaces the file once signing succeeded, so trying again is safe.
MAX_ATTEMPTS=3

# Usage: azure_signing_init PSIGN OSSLSIGNCODE WORK_DIR ROOT_PEM...
azure_signing_init() {
    PSIGN="$1"
    OSSLSIGNCODE="$2"
    WORK="$3"
    shift 3

    local var value
    for var in "${AZURE_SIGNING_VARS[@]}"; do
        if [ -z "${!var:-}" ]; then
            echo "error: ${var} is not set" >&2
            return 2
        fi
    done

    cat "$@" >"$WORK/roots.pem"

    # The values go into JSON unescaped, so refuse anything that would need escaping.
    for value in "$AZURE_ARTIFACT_SIGNING_ENDPOINT" "$AZURE_ARTIFACT_SIGNING_ACCOUNT" \
        "$AZURE_ARTIFACT_SIGNING_PROFILE" "$AZURE_ARTIFACT_SIGNING_CORRELATION_ID"; do
        case "$value" in
            *[\"\\]*)
                echo "error: Azure signing settings must not contain quotes or backslashes" >&2
                return 2
                ;;
        esac
    done
    printf '{"Endpoint": "%s", "CodeSigningAccountName": "%s", "CertificateProfileName": "%s", "CorrelationId": "%s"}\n' \
        "$AZURE_ARTIFACT_SIGNING_ENDPOINT" "$AZURE_ARTIFACT_SIGNING_ACCOUNT" \
        "$AZURE_ARTIFACT_SIGNING_PROFILE" "$AZURE_ARTIFACT_SIGNING_CORRELATION_ID" >"$WORK/metadata.json"
}

_azure_sign() {
    AZURE_TENANT_ID="$AZURE_ARTIFACT_SIGNING_TENANT_ID" \
        AZURE_CLIENT_ID="$AZURE_ARTIFACT_SIGNING_CLIENT_ID" \
        AZURE_CLIENT_SECRET="$AZURE_ARTIFACT_SIGNING_CLIENT_SECRET" \
        "$PSIGN" --mode portable sign \
        --digest sha256 \
        --artifact-signing-metadata "$WORK/metadata.json" \
        --timestamp-url "$TSA_URL" --timestamp-digest sha256 \
        "$1"
}

_azure_sign_with_retry() {
    local attempt
    for ((attempt = 1; ; attempt++)); do
        if _azure_sign "$1"; then
            return 0
        fi
        if ((attempt >= MAX_ATTEMPTS)); then
            return 1
        fi
        echo "warning: signing $1 failed (attempt $attempt of $MAX_ATTEMPTS), retrying in $((10 * attempt)) s" >&2
        sleep $((10 * attempt))
    done
}

# Same call as tests/packaging/test_files.py (_verify_signature), but
# osslsigncode exits 0 even when the timestamp check failed, so that result is
# checked separately.
_azure_verify() {
    local log="$WORK/verify.log"
    if ! "$OSSLSIGNCODE" verify -ignore-cdp -ignore-crl \
        -CAfile "$WORK/roots.pem" -TSA-CAfile "$WORK/roots.pem" -in "$1" >"$log" 2>&1; then
        cat "$log" >&2
        return 1
    fi
    if ! grep -q "^Timestamp Server Signature verification: ok" "$log"; then
        grep "Timestamp" "$log" >&2 || echo "no timestamp found" >&2
        return 1
    fi
    # The first subject in the log is the one of the signing certificate,
    # the timestamp and CA chains follow. Catches a wrong certificate profile
    # or a foreign signature that was already there.
    local signer
    signer="$(sed -n 's/^[[:space:]]*Subject: //p' "$log" | head -1)"
    if [[ "$signer" != "$EXPECTED_SIGNER"* ]]; then
        echo "unexpected signer: ${signer:-none}" >&2
        return 1
    fi
}

# Signs the given files in place and verifies them; fails if any of them fails.
azure_sign_files() {
    local file failed=0
    for file in "$@"; do
        if _azure_sign_with_retry "$file" && _azure_verify "$file"; then
            echo "signed and verified: $file"
        else
            echo "error: signing or verification failed: $file" >&2
            failed=1
        fi
    done
    return "$failed"
}
