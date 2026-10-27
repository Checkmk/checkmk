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
#   DELTA              runfiles path of //bazel/tools/delta, which lists the files
#                      for --delta
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

: "${FORMAT_LANGS:?}" "${FORMAT_SH:?}" "${FORMAT_MODE:?}" "${FORMAT_FIX_TARGET:?}" "${FORMAT_CACHE:?}" "${DELTA:?}"
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

# Prints a slot's output. With --delta, it leaves out format.sh's timings, which
# the summary replaces.
print_slot_output() { # <output file>
    if [ "$delta" = true ]; then
        grep -v -E '^Formatted .+ in [0-9]+m[0-9.]+s$' "$1" || true
    else
        cat "$1"
    fi
}

# --- --delta: format only the files changed compared to the base branch ---

# Succeeds if --delta is among the arguments.
has_delta_arg() { # <argument>...
    local arg
    for arg in "$@"; do
        if [ "$arg" = --delta ]; then
            return 0
        fi
    done
    return 1
}

# Sets delta_files to the files changed compared to the base branch and
# base_branch to that branch, as listed by //bazel/tools/delta. Exits if files
# are passed along with --delta, or if no file changed. Changes into the
# workspace, as the files are relative to it: format.sh changes into the
# directory the command runs from.
collect_delta_files() { # <argument>...
    local target=$FORMAT_FIX_TARGET
    if [ "$FORMAT_MODE" = check ]; then
        target+=.check
    fi
    if [ $# -gt 1 ]; then
        echo >&2 "ERROR: passing files together with --delta is not supported."
        echo >&2 "Use either 'bazel run $target -- --delta' or 'bazel run $target -- <files>'."
        exit 1
    fi
    # The base branch, then the files, each terminated by a NUL byte
    "$(rlocation "$DELTA")" files >"$output_dir/delta" || exit 1
    mapfile -d '' -t delta_files <"$output_dir/delta"
    base_branch=${delta_files[0]}
    delta_files=("${delta_files[@]:1}")
    cd "$BUILD_WORKSPACE_DIRECTORY"
    if [ ${#delta_files[@]} -eq 0 ]; then
        echo "No files changed compared to $base_branch."
        exit 0
    fi
}

# Sets summary_rows to how many of delta_files each language formats and how
# many no formatter takes, as "<label>|<count>".
collect_summary_rows() {
    local language tool handled
    local handled_files=() language_files=()
    summary_rows=()
    while IFS='|' read -r _ language tool _; do
        mapfile -t language_files < <(ls-files "$language" "${delta_files[@]}")
        if [ ${#language_files[@]} -gt 0 ]; then
            summary_rows+=("$language (${tool##*/}):|${#language_files[@]}")
            handled_files+=("${language_files[@]}")
        fi
    done <"$(rlocation "$FORMAT_LANGS")"
    handled=$(printf '%s\n' "${handled_files[@]}" | sort -u | grep -c .) || true
    if [ "$handled" -lt ${#delta_files[@]} ]; then
        summary_rows+=("Skipped (no formatter):|$((${#delta_files[@]} - handled))")
    fi
}

# Prints "<hash> <file>" for every modified or untracked file of the workspace.
dirty_file_hashes() {
    local file
    local -a files=()
    while IFS= read -r -d '' file; do
        if [ -f "$file" ]; then
            files+=("$file")
        fi
    done < <(git ls-files -z --modified --others --exclude-standard)
    if [ ${#files[@]} -gt 0 ]; then
        paste -d ' ' <(printf '%s\n' "${files[@]}" | git hash-object --stdin-paths) <(printf '%s\n' "${files[@]}")
    fi
}

# Prints the files that changed since dirty_file_hashes printed the given
# hashes, or that nothing needed formatting.
print_formatted_files() { # <hashes before>
    local file
    local -a changed
    # A changed file is new among the dirty files or has another hash than before
    mapfile -t changed < <(
        comm -13 <(sort <<<"$1") <(dirty_file_hashes | sort) | cut -d' ' -f2- | sort -u | grep .
    )
    if [ ${#changed[@]} -eq 0 ]; then
        print_delta_note "Nothing needed formatting."
        return
    fi
    print_delta_note "Formatted ${#changed[@]} file(s):"
    for file in "${changed[@]}"; do
        print_delta_note "  $file"
    done
}

# Prints the message indented, in yellow if stdout is a terminal.
print_delta_note() { # <message>
    if [ -t 1 ]; then
        echo $'\e[33m'"  $1"$'\e[0m'
    else
        echo "  $1"
    fi
}

# Prints the title and below it a row per "<label>|<count>", with the counts in
# an aligned column, framed by blank lines.
print_delta_summary() { # <title> <label>|<count>...
    local title=$1 row label count label_width=0 count_width=0
    shift
    for row in "$@"; do
        label=${row%|*} count=${row##*|}
        if [ ${#label} -gt "$label_width" ]; then
            label_width=${#label}
        fi
        if [ ${#count} -gt "$count_width" ]; then
            count_width=${#count}
        fi
    done
    echo
    print_delta_note "$title"
    for row in "$@"; do
        print_delta_note "$(printf '  %-*s %*s' "$label_width" "${row%|*}" "$count_width" "${row##*|}")"
    done
    echo
}

# Prints the summary of formatting delta_files and its outcome: whether the
# check found problems, or which files the fix changed.
print_delta_outcome() { # <hashes before, in fix mode>
    local title=Formatting
    if [ "$FORMAT_MODE" = check ]; then
        title+=" (check only)"
    fi
    print_delta_summary "$title: ${#delta_files[@]} file(s) changed compared to $base_branch" "${summary_rows[@]}"
    if [ "$FORMAT_MODE" = fix ]; then
        print_formatted_files "$1"
        if [ ${#failed[@]} -gt 0 ]; then
            print_delta_note "Formatter errors above."
        fi
    elif [ ${#failed[@]} -eq 0 ]; then
        print_delta_note "No formatting problems."
    else
        print_delta_note "Formatting problems above."
    fi
}

# --- main ---

output_dir=$(mktemp -d)
trap 'rm -rf "$output_dir"' EXIT

# --delta replaces the paths with the files changed on the branch.
requested_args=$*
delta=false
if has_delta_arg "$@"; then
    delta=true
    collect_delta_files "$@"
    collect_summary_rows
    hashes_before=""
    if [ "$FORMAT_MODE" = fix ]; then
        hashes_before=$(dirty_file_hashes)
    fi
    set -- "${delta_files[@]}"
fi

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
    print_slot_output "$output_dir/$i"
    [ "$code" -eq 0 ] || failed+=("${languages[$i]} ($code)")
done

if [ ${#failed[@]} -gt 0 ]; then
    echo >&2 "FAILED: formatter exited non-zero: ${failed[*]}"
    if [ "$FORMAT_MODE" = check ]; then
        echo >&2 "Try running 'bazel run $FORMAT_FIX_TARGET -- $requested_args' to fix this."
    fi
fi
if [ "$delta" = true ]; then
    print_delta_outcome "$hashes_before"
fi
[ ${#failed[@]} -eq 0 ]
