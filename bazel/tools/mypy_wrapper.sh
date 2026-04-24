#!/bin/bash
# Filter MYPYPATH to drop rules_python namespace-package entries for meraki,
# which otherwise cause mypy "Source file found twice" errors.

set -eu

# --- begin runfiles.bash initialization v3 ---
# Copy-pasted from Bazel's Bash runfiles library v3.
if [[ ! -d "${RUNFILES_DIR:-/dev/null}" && ! -f "${RUNFILES_MANIFEST_FILE:-/dev/null}" ]]; then
    if [[ -f "$0.runfiles_manifest" ]]; then
        export RUNFILES_MANIFEST_FILE="$0.runfiles_manifest"
    elif [[ -f "$0.runfiles/MANIFEST" ]]; then
        export RUNFILES_MANIFEST_FILE="$0.runfiles/MANIFEST"
    elif [[ -d "$0.runfiles" ]]; then
        export RUNFILES_DIR="$0.runfiles"
    fi
fi
# --- end runfiles.bash initialization v3 ---

filtered=""
IFS=':'
for p in ${MYPYPATH:-}; do
    case "$p" in
        *_meraki/site-packages*) ;;
        *)
            if [ -n "$filtered" ]; then
                filtered="$filtered:$p"
            else
                filtered="$p"
            fi
            ;;
    esac
done
unset IFS
export MYPYPATH="$filtered"

if [[ -n "${RUNFILES_DIR:-}" ]]; then
    exec "$RUNFILES_DIR/_main/bazel/tools/mypy_cli_original" "$@"
elif [[ -n "${RUNFILES_MANIFEST_FILE:-}" ]]; then
    target=$(grep -m1 '^_main/bazel/tools/mypy_cli_original ' "$RUNFILES_MANIFEST_FILE" | cut -d' ' -f2-)
    exec "$target" "$@"
else
    echo "mypy_wrapper.sh: cannot locate runfiles" >&2
    exit 1
fi
