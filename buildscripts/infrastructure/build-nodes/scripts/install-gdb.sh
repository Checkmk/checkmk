#!/bin/bash
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

set -e -o pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" >/dev/null 2>&1 && pwd)"
# shellcheck source=buildscripts/infrastructure/build-nodes/scripts/build_lib.sh
. "${SCRIPT_DIR}/build_lib.sh"

MIRROR_URL="https://ftp.gnu.org/gnu/"

GCC_MAJOR=$(get_version "$SCRIPT_DIR" GCC_VERSION_MAJOR)
GCC_MINOR=$(get_version "$SCRIPT_DIR" GCC_VERSION_MINOR)
GCC_PATCHLEVEL=$(get_version "$SCRIPT_DIR" GCC_VERSION_PATCHLEVEL)
GCC_VERSION="${GCC_MAJOR}.${GCC_MINOR}.${GCC_PATCHLEVEL}"

PYTHON_VERSION=$(get_version "$SCRIPT_DIR" PYTHON_VERSION)

GDB_VERSION="13.2"
GDB_ARCHIVE_NAME="gdb-${GDB_VERSION}.tar.gz"
GDB_URL="${MIRROR_URL}gdb/${GDB_ARCHIVE_NAME}"

DIR_NAME=gdb-${GDB_VERSION}
TARGET_DIR="${TARGET_DIR:-/opt}"
PREFIX=${TARGET_DIR}/${DIR_NAME}
GCC_PREFIX=${TARGET_DIR}/gcc-${GCC_VERSION}
BUILD_DIR="${TARGET_DIR}/src"

# Increase this to enforce a recreation of the build cache
# GDB requires libpython3.12.so.1.0, depending on the Python version
BUILD_ID="${GDB_VERSION}-${PYTHON_VERSION}-1"

download_sources() {
    # Get the sources from nexus or upstream
    mirrored_download "${GDB_ARCHIVE_NAME}" "${GDB_URL}"
}

build_gdb() {
    log "Build gdb-${GDB_VERSION}"
    cd "${BUILD_DIR}"
    tar xzf gdb-${GDB_VERSION}.tar.gz
    # remove potential older build directories
    if [[ -d gdb-${GDB_VERSION}-build ]]; then
        rm -rf "gdb-${GDB_VERSION}-build"
    fi
    mkdir gdb-${GDB_VERSION}-build
    cd gdb-${GDB_VERSION}-build
    ../gdb-${GDB_VERSION}/configure \
        --prefix="${PREFIX}" \
        CC="${GCC_PREFIX}/bin/gcc-${GCC_MAJOR}" \
        CXX="${GCC_PREFIX}/bin/g++-${GCC_MAJOR}" \
        "$(python -V 2>&1 | grep -q 'Python 2\.4\.' && echo "--with-python=no")"
    make -j4
    make install
}

set_symlinks() {
    log "Set symlink"

    # We should not mess with the files below /usr/bin. Instead we should only deploy to /opt/bin to
    # prevent conflicts.
    # Right now it seems binutils is installed by install-cmk-dependencies.sh which then overwrites
    # our /usr/bin/as symlink. As an intermediate fix, we additionally install the link to /opt/bin.
    # As a follow-up, we should move everything to /opt/bin - but that needs separate testing.
    [ -d "${TARGET_DIR}/bin" ] || mkdir -p "${TARGET_DIR}/bin"
    ln -sf "${PREFIX}/bin/"* "${TARGET_DIR}"/bin

    ln -sf "${PREFIX}/bin/"* /usr/bin
}

build_package() {
    mkdir -p "$TARGET_DIR/src"
    cd "$TARGET_DIR/src"

    download_sources
    build_gdb

    cd "$TARGET_DIR"
    rm -rf "$TARGET_DIR/src"
}

if [ "$1" != "link-only" ]; then
    cached_build "${TARGET_DIR}" "${DIR_NAME}" "${BUILD_ID}" "${DISTRO}" "${BRANCH_VERSION}"
fi
set_symlinks

test_package "/usr/bin/gdb --version" "$GDB_VERSION"
