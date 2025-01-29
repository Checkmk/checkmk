#!/usr/bin/env bash

set -e

DONT_STRIP=(
    # To make our debugging life easier, don't strip our Livestatus library.
    "liblivestatus.so*"
    "strip"
    "strip_binaries.sh"
    # When the library libLLVM-${llvm_version}-rust-${rust_version}-${rust_channel}.so is stripped, rustc (and other
    # binaries which link against this library) will segfault.
    # https://github.com/rust-lang/rust/issues/112286
    "libLLVM*rust*.so*"
    "libLLVM*.so*rust*"
    # Stripping these rust libs leads to a segmentation fault on rustc 1.75 & 1.76.
    "libstd-*.so"
    "librustc_driver-*.so"
    "don*t"
)

is_so_or_exec_elf_file() {
    file_type=$(file "$1")

    if [[ $file_type == *"shared object"* ]]; then
        return 0
    fi

    if [[ $file_type == *"ELF"*"executable"* ]]; then
        return 0
    fi
    return 1
}

is_executable() {
    local file="$1"
    if [[ -x "$file" ]]; then
        return 0
    else
        return 1
    fi
}

is_static_library() {
    [[ "$(basename "$")" == lib*.a ]]
}

strip_binary() {
    # Arguments taken from debhelper dh_strip (Ubuntu 20.04)
    strip --remove-section=.comment --remove-section=.note "$1"
}

strip_shared_library() {
    # Arguments taken from debhelper dh_strip (Ubuntu 20.04)
    strip --remove-section=.comment --remove-section=.note --strip-unneeded "$1"
}

strip_static_library() {
    # Arguments taken from debhelper dh_strip (Ubuntu 20.04)
    strip --strip-debug --remove-section=.comment --remove-section=.note --enable-deterministic-archives \
        -R .gnu.lto_* -R .gnu.debuglto_* -N __gnu_lto_slim -N __gnu_lto_v1 "$1"
}

iter_files() {
    find "$1" -type f ! -type l
}

for i in "$@"; do
    case $i in
    --exclude=*)
        IFS=',' read -ra EXCLUDE <<<"${i#*=}"
        shift
        ;;
    --path=*)
        path_to_strip="${i#*=}"
        shift
        ;;
    esac
done

iter_files "$path_to_strip" | while read -r current_file; do
    for dont in "${DONT_STRIP[@]}"; do
        if [[ "$(basename "$current_file")" == $dont ]]; then
            continue 2
        fi
    done
    for exclude in "${EXCLUDE[@]}"; do
        if [ "$(basename "$current_file")" = "$exclude" ]; then
            continue 2
        fi
    done
    if is_so_or_exec_elf_file "$current_file"; then
        if is_executable "$current_file"; then
            strip_binary "$current_file"
        else
            strip_shared_library "$current_file"
        fi
    elif is_static_library "$current_file"; then
        strip_static_library "$current_file"
    fi
done
