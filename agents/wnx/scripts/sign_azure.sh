#!/usr/bin/env bash
# Authenticode-sign Windows artifacts in place with psign via Azure Artifact
# Signing, then verify each signature and its RFC 3161 timestamp.
#
# Usage: bazel run //agents/wnx/scripts:sign_azure -- FILE...
#        (FILE paths are relative to the workspace root)
#
# Environment:
#   AZURE_ARTIFACT_SIGNING_ENDPOINT, _ACCOUNT, _PROFILE
#   AZURE_ARTIFACT_SIGNING_TENANT_ID, _CLIENT_ID, _CLIENT_SECRET
#   AZURE_ARTIFACT_SIGNING_CORRELATION_ID
#
# No secret is passed on a command line: psign reads the service principal from
# AZURE_* env vars, and the metadata file with the CorrelationId lives in a
# 0700 temp dir that is removed on exit.
set -euo pipefail

# --- begin runfiles.bash initialization v3 ---
# shellcheck disable=SC1090,SC1091
{
    set -o pipefail
    set +e
    f=bazel_tools/tools/bash/runfiles/runfiles.bash
    source "${RUNFILES_DIR:-/dev/null}/$f" 2>/dev/null ||
        source "$(grep -sm1 "^$f " "${RUNFILES_MANIFEST_FILE:-/dev/null}" | cut -f2- -d' ')" 2>/dev/null ||
        source "$0.runfiles/$f" 2>/dev/null ||
        source "$(grep -sm1 "^$f " "$0.runfiles_manifest" | cut -f2- -d' ')" 2>/dev/null ||
        source "$(grep -sm1 "^$f " "$0.exe.runfiles_manifest" | cut -f2- -d' ')" 2>/dev/null ||
        {
            echo >&2 "ERROR: cannot find runfiles.bash"
            exit 1
        }
    f=
    set -e
}
# --- end runfiles.bash initialization v3 ---

TSA_URL="http://timestamp.acs.microsoft.com"
# Start of the subject of the certificate Artifact Signing issues for our profile.
EXPECTED_SIGNER="CN=Checkmk GmbH,O=Checkmk GmbH,"

if [ -z "${BUILD_WORKSPACE_DIRECTORY:-}" ]; then
    echo "error: run this via 'bazel run //agents/wnx/scripts:sign_azure -- FILE...'" >&2
    exit 2
fi

# Set by the sh_binary (env attribute).
PSIGN="$(rlocation "$SIGN_AZURE_PSIGN")"
OSSLSIGNCODE="$(rlocation "$SIGN_AZURE_OSSLSIGNCODE")"
read -r -a roots <<<"$SIGN_AZURE_ROOTS"

if [ "$#" -eq 0 ]; then
    echo "error: no files to sign given" >&2
    exit 2
fi
for var in AZURE_ARTIFACT_SIGNING_ENDPOINT AZURE_ARTIFACT_SIGNING_ACCOUNT \
    AZURE_ARTIFACT_SIGNING_PROFILE AZURE_ARTIFACT_SIGNING_TENANT_ID \
    AZURE_ARTIFACT_SIGNING_CLIENT_ID AZURE_ARTIFACT_SIGNING_CLIENT_SECRET \
    AZURE_ARTIFACT_SIGNING_CORRELATION_ID; do
    if [ -z "${!var:-}" ]; then
        echo "error: ${var} is not set" >&2
        exit 2
    fi
done

WORK="$(mktemp -d)" # 0700
trap 'rm -rf "$WORK"' EXIT

for root in "${roots[@]}"; do
    cat "$(rlocation "$root")"
done >"$WORK/roots.pem"

correlation_id="$AZURE_ARTIFACT_SIGNING_CORRELATION_ID"
# The values go into JSON unescaped, so refuse anything that would need escaping.
for value in "$AZURE_ARTIFACT_SIGNING_ENDPOINT" "$AZURE_ARTIFACT_SIGNING_ACCOUNT" \
    "$AZURE_ARTIFACT_SIGNING_PROFILE" "$correlation_id"; do
    case "$value" in
        *[\"\\]*)
            echo "error: Azure signing settings must not contain quotes or backslashes" >&2
            exit 2
            ;;
    esac
done
printf '{"Endpoint": "%s", "CodeSigningAccountName": "%s", "CertificateProfileName": "%s", "CorrelationId": "%s"}\n' \
    "$AZURE_ARTIFACT_SIGNING_ENDPOINT" "$AZURE_ARTIFACT_SIGNING_ACCOUNT" \
    "$AZURE_ARTIFACT_SIGNING_PROFILE" "$correlation_id" >"$WORK/metadata.json"

sign() {
    AZURE_TENANT_ID="$AZURE_ARTIFACT_SIGNING_TENANT_ID" \
        AZURE_CLIENT_ID="$AZURE_ARTIFACT_SIGNING_CLIENT_ID" \
        AZURE_CLIENT_SECRET="$AZURE_ARTIFACT_SIGNING_CLIENT_SECRET" \
        "$PSIGN" --mode portable sign \
        --digest sha256 \
        --artifact-signing-metadata "$WORK/metadata.json" \
        --timestamp-url "$TSA_URL" --timestamp-digest sha256 \
        "$1"
}

# Same call as tests/packaging/test_files.py (_verify_signature), but
# osslsigncode exits 0 even when the timestamp check failed, so that result is
# checked separately.
verify() {
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

cd "$BUILD_WORKSPACE_DIRECTORY"
failed=0
for file in "$@"; do
    if sign "$file" && verify "$file"; then
        echo "signed and verified: $file"
    else
        echo "error: signing or verification failed: $file" >&2
        failed=1
    fi
done
exit "$failed"
