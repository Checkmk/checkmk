#!/usr/bin/env bash
# Authenticode-sign Windows artifacts in place with psign via Azure Artifact
# Signing, then verify each signature and its RFC 3161 timestamp.
#
# Usage: bazel run //bazel/rules:sign_azure -- FILE...
#        (FILE paths are relative to the workspace root)
#
# Environment: the AZURE_ARTIFACT_SIGNING_* settings, see azure_signing.sh.
set -euo pipefail

if [ -z "${BUILD_WORKSPACE_DIRECTORY:-}" ]; then
    echo "error: run this via 'bazel run //bazel/rules:sign_azure -- FILE...'" >&2
    exit 2
fi

if [ "$#" -eq 0 ]; then
    echo "error: no files to sign given" >&2
    exit 2
fi

# Set by the sh_binary (env attribute).
# shellcheck disable=SC1090,SC1091 # azure_signing.sh, passed in by the caller
source "$(rlocation "$SIGN_AZURE_LIB")"
read -r -a roots <<<"$SIGN_AZURE_ROOTS"
root_files=()
for root in "${roots[@]}"; do
    root_files+=("$(rlocation "$root")")
done

WORK="$(mktemp -d)" # 0700
trap 'rm -rf "$WORK"' EXIT
azure_signing_init "$(rlocation "$SIGN_AZURE_PSIGN")" "$(rlocation "$SIGN_AZURE_OSSLSIGNCODE")" \
    "$WORK" "${root_files[@]}"

cd "$BUILD_WORKSPACE_DIRECTORY"
azure_sign_files "$@"
