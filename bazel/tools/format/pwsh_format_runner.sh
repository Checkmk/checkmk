#!/usr/bin/env bash
# Wrapper that bridges format_multirun's invocation contract to pwsh_format.ps1.
# Mirrors the pattern of shfmt and taplo_quiet in this directory.

set -euo pipefail

# --- begin runfiles.bash initialization v3 ---
# https://github.com/bazelbuild/bazel/blob/master/tools/bash/runfiles/runfiles.bash
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

cd "${BUILD_WORKSPACE_DIRECTORY:=.}" || exit 1

PWSH="$(rlocation +repos+pwsh/pwsh)"
SCRIPT="$(rlocation _main/bazel/tools/format/pwsh_format.ps1)"
PSSA_PSD1="$(rlocation +repos+psscriptanalyzer/PSScriptAnalyzer.psd1)"

# Parse rules_lint-style flags into Check switch + remaining file args.
extra_args=()
files=()
for arg in "$@"; do
    case "$arg" in
        --check) extra_args+=("-Check") ;;
        *) files+=("$arg") ;;
    esac
done

# If no files passed, exit cleanly (xargs may invoke us with no args when the file list is empty).
if [[ ${#files[@]} -eq 0 ]]; then
    exit 0
fi

exec "$PWSH" -NonInteractive -NoProfile -File "$SCRIPT" \
    -PssaPsd1 "$PSSA_PSD1" \
    "${extra_args[@]}" \
    "${files[@]}"
