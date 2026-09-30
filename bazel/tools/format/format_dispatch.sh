#!/usr/bin/env bash
# Single-process driver for the rules_lint formatters, see format_dispatch.bzl.
#
# rules_lint's format_multirun starts one wrapper per language, each of which
# initialises the runfiles library twice and scans the arguments before it
# finds out that it has nothing to do. This script sources rules_lint's
# format.sh once and runs its per-language routine in forked subshells.
#
# Configuration comes from the environment, set by format_dispatch():
#   FORMAT_LANGS       runfiles path of a "<slot>|<language>|<tool>|<flags>" table
#   FORMAT_SH          runfiles path of rules_lint's format.sh
#   FORMAT_MODE        "fix" or "check"
#   FORMAT_FIX_TARGET  target to suggest when a check fails
#   FORMAT_CACHE       workspace-relative directory for the formatters' caches
#
# Each formatter runs with FORMAT_CACHE_DIR set to an absolute directory of its
# own below FORMAT_CACHE, one per language, where it may keep a cache.

set -eo pipefail

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

: "${FORMAT_LANGS:?}" "${FORMAT_SH:?}" "${FORMAT_MODE:?}" "${FORMAT_FIX_TARGET:?}" "${FORMAT_CACHE:?}"
runfiles_export_envvars

# Sourcing format.sh defines ls-files and process_args_in_batches, changes into
# BUILD_WORKSPACE_DIRECTORY, enables `set -u` and installs an EXIT trap that is
# replaced below. Its functions read `mode` and `disable_git_attribute_checks`.
export mode="$FORMAT_MODE" disable_git_attribute_checks=false
# shellcheck disable=SC1090
source "$(rlocation "$FORMAT_SH")"

# Mirrors the main block of format.sh. The table lists the dialects that
# format.sh handles along with JavaScript and CSS as languages of their own.
format_language() { # <language> <tool> <flags> [<path>...]
    local language=$1 tool=$2 flags=$3
    shift 3
    local bin
    bin="$(rlocation "$tool")"
    [ -e "$bin" ] || {
        echo >&2 "cannot locate binary $tool"
        exit 1
    }
    export FORMAT_CACHE_DIR="$BUILD_WORKSPACE_DIRECTORY/$FORMAT_CACHE/$language"
    process_args_in_batches "$language" "$bin" "$flags" "$@"
}

# Formats the languages of a slot one after the other and keeps going after
# failures. Slots run in parallel.
format_slot() { # <"<language>|<tool>|<flags>" lines> [<path>...]
    local specs=$1 language tool flags code=0
    shift
    while IFS='|' read -r language tool flags; do
        # In the background, as `set -e` would not apply within `(...) || code=$?`.
        (format_language "$language" "$tool" "$flags" "$@") </dev/null &
        wait $! || code=$?
    done <<<"$specs"
    return "$code"
}

output_dir=$(mktemp -d)
trap 'rm -rf "$output_dir"' EXIT

slots=()     # per slot: its "<language>|<tool>|<flags>" lines
languages=() # per slot: its languages, for the summary
while IFS='|' read -r slot language tool flags; do
    if [ "$slot" != "${previous_slot:-}" ]; then
        slots+=("")
        languages+=("")
        previous_slot=$slot
    fi
    slots[-1]+="${slots[-1]:+$'\n'}$language|$tool|$flags"
    languages[-1]+="${languages[-1]:+, }$language"
done <"$(rlocation "$FORMAT_LANGS")"

pids=()
for specs in "${slots[@]}"; do
    (format_slot "$specs" "$@") >"$output_dir/${#pids[@]}" 2>&1 &
    pids+=("$!")
done

# Like rules_multirun with buffer_output: print each slot's output once it has
# finished, in table order, and keep going after failures.
failed=()
for i in "${!pids[@]}"; do
    if wait "${pids[$i]}"; then
        code=0
    else
        code=$?
    fi
    cat "$output_dir/$i"
    [ "$code" -eq 0 ] || failed+=("${languages[$i]} ($code)")
done

[ ${#failed[@]} -eq 0 ] && exit 0
echo >&2 "FAILED: formatter exited non-zero: ${failed[*]}"
if [ "$FORMAT_MODE" = check ]; then
    echo >&2 "Try running 'bazel run $FORMAT_FIX_TARGET -- $*' to fix this."
fi
exit 1
