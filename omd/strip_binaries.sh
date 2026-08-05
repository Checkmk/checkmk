#!/usr/bin/env bash
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
#
# Searches a tree for binaries and libraries to strip and strips them.
#
# Inspired by debhelpers dh_strip which is doing a good job stripping
# executables, shared libraries and some static libraries during packaging of
# deb packages.
#
# It allows us to strip all binaries and libraries except some we want to
# exclude from stripping. For example bin/cmc is a binary we want to have debug
# symbols for.
#
# Bash port of the original strip_binaries.py.

set -uo pipefail

# --- ELF constants ----------------------------------------------------------

# The ELF header is at least 0x32 bytes (32bit); any file shorter than that is
# not an ELF file.
readonly ELF_MIN_LENGTH=32
readonly ELF_MAGIC="7f454c46" # "\x7fELF"
readonly ELF_ENDIAN_LE="01"
readonly ELF_ENDIAN_BE="02"
readonly ELF_VERSION=1
readonly ELF_TYPE_EXECUTABLE=2
readonly ELF_TYPE_SHARED_OBJECT=3

# --- Files we never strip ---------------------------------------------------
DONT_STRIP=(
    # To make our debugging life easier, don't strip our Livestatus library.
    "liblivestatus.so*"
    "strip"
    # When the library libLLVM-*-rust-*.so is stripped, rustc (and other
    # binaries which link against this library) will segfault.
    # https://github.com/rust-lang/rust/issues/112286
    "libLLVM*rust*.so*"
    "libLLVM*.so*rust*"
    # Stripping these rust libs leads to a segfault on rustc 1.75 & 1.76.
    "libstd-*.so"
    "librustc_driver-*.so"
)

# --- Argument parsing -------------------------------------------------------

usage() {
    cat <<'EOF'
Usage: strip_binaries.sh [--exclude STRING]... PATH

Searches PATH for files to be stripped.

  --exclude STRING   Exclude files that contain the given string anywhere in
                     their path from being stripped. May be used multiple times.
EOF
}

PATH_ARG=""
EXCLUDES=()

parse_arguments() {
    local seen_path=0
    while [ $# -gt 0 ]; do
        case "$1" in
            --exclude)
                shift
                [ $# -gt 0 ] || {
                    echo "error: --exclude needs an argument" >&2
                    exit 2
                }
                EXCLUDES+=("$1")
                ;;
            --exclude=*)
                EXCLUDES+=("${1#--exclude=}")
                ;;
            -h | --help)
                usage
                exit 0
                ;;
            --)
                shift
                break
                ;;
            -*)
                echo "error: unknown option: $1" >&2
                exit 2
                ;;
            *)
                if [ "$seen_path" -eq 1 ]; then
                    echo "error: unexpected argument: $1" >&2
                    exit 2
                fi
                PATH_ARG="$1"
                seen_path=1
                ;;
        esac
        shift
    done

    # Positional args after "--"
    while [ $# -gt 0 ]; do
        if [ "$seen_path" -eq 1 ]; then
            echo "error: unexpected argument: $1" >&2
            exit 2
        fi
        PATH_ARG="$1"
        seen_path=1
        shift
    done

    if [ "$seen_path" -eq 0 ]; then
        echo "error: the following argument is required: path" >&2
        usage >&2
        exit 2
    fi
}

# --- File classification ----------------------------------------------------

is_excluded() {
    # Returns 0 (true) if the path contains any of the exclude strings.
    local path="$1" e
    for e in ${EXCLUDES[@]+"${EXCLUDES[@]}"}; do
        case "$path" in
            *"$e"*) return 0 ;;
        esac
    done
    return 1
}

is_so_or_exec_elf_file() {
    local file="$1" head magic endian e_type_hex e_vers_hex e_type e_vers

    # Read the first ELF_MIN_LENGTH bytes as a flat hex string.
    head=$(od -A n -v -t x1 -N "$ELF_MIN_LENGTH" -- "$file" 2>/dev/null | tr -d ' \n')

    # Each byte is two hex chars. Anything shorter than the header is not ELF.
    [ "${#head}" -eq $((ELF_MIN_LENGTH * 2)) ] || return 1

    magic="${head:0:8}"
    [ "$magic" = "$ELF_MAGIC" ] || return 1

    # EI_DATA (endianness) is byte 0x05 -> hex offset 10.
    endian="${head:10:2}"
    if [ "$endian" = "$ELF_ENDIAN_BE" ]; then
        # big endian: bytes already in natural order
        e_type_hex="${head:32:4}" # e_type  @0x10 (2 bytes)
        e_vers_hex="${head:40:8}" # e_version @0x14 (4 bytes)
    elif [ "$endian" = "$ELF_ENDIAN_LE" ]; then
        # little endian: reverse the byte order
        e_type_hex="${head:34:2}${head:32:2}"
        e_vers_hex="${head:46:2}${head:44:2}${head:42:2}${head:40:2}"
    else
        return 1
    fi

    e_type=$((16#$e_type_hex))
    e_vers=$((16#$e_vers_hex))

    [ "$e_vers" -eq "$ELF_VERSION" ] || return 1
    [ "$e_type" -eq "$ELF_TYPE_EXECUTABLE" ] || [ "$e_type" -eq "$ELF_TYPE_SHARED_OBJECT" ]
}

is_static_library() {
    local name="${1##*/}"
    [[ "$name" == lib*.a ]]
}

is_executable() {
    # Mirror the original: check the owner execute bit (S_IEXEC, 0o100).
    local mode
    mode=$(stat -c '%a' -- "$1" 2>/dev/null) || return 1
    (((8#$mode & 8#100) == 8#100))
}

# --- Stripping --------------------------------------------------------------

should_not_strip() {
    local name="${1##*/}" pat
    for pat in "${DONT_STRIP[@]}"; do
        # shellcheck disable=SC2053  # intentional glob match
        [[ "$name" == $pat ]] && return 0
    done
    return 1
}

run_strip() {
    local file="${!#}" # last positional arg is the file
    if should_not_strip "$file"; then
        return 0
    fi
    printf 'Strip: %s\n' "$file"
    if ! /usr/bin/strip "$@"; then
        printf 'strip failed for %s\n' "$file" >&2
        return 1
    fi
}

strip_binary() {
    # Arguments taken from debhelper dh_strip (Ubuntu 20.04)
    run_strip --remove-section=.comment --remove-section=.note "$1"
}

strip_shared_library() {
    # Arguments taken from debhelper dh_strip (Ubuntu 20.04)
    run_strip --remove-section=.comment --remove-section=.note --strip-unneeded "$1"
}

strip_static_library() {
    # Arguments taken from debhelper dh_strip (Ubuntu 20.04)
    run_strip \
        --strip-debug \
        --remove-section=.comment \
        --remove-section=.note \
        --enable-deterministic-archives \
        -R ".gnu.lto_*" \
        -R ".gnu.debuglto_*" \
        -N "__gnu_lto_slim" \
        -N "__gnu_lto_v1" \
        "$1"
}

# --- Main -------------------------------------------------------------------

main() {
    parse_arguments "$@"

    local file
    while IFS= read -r -d '' file; do
        is_excluded "$file" && continue

        if is_so_or_exec_elf_file "$file"; then
            if is_executable "$file"; then
                strip_binary "$file" || return 1
            else
                strip_shared_library "$file" || return 1
            fi
        elif is_static_library "$file"; then
            strip_static_library "$file" || return 1
        fi
    done < <(find "$PATH_ARG" -type f -print0)

    printf 'Done done done\n'
    return 0
}

if [[ "${BASH_SOURCE[0]}" == "${0}" ]]; then
    main "$@"
fi
