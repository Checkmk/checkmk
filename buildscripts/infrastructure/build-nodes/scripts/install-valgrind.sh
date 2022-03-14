#!/bin/bash
# Copyright (C) 2021 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

set -e -o pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" >/dev/null 2>&1 && pwd)"
# shellcheck source=build_lib.sh
. "${SCRIPT_DIR}/build_lib.sh"

TARGET_DIR="${TARGET_DIR:-/opt}"

VALGRIND_VERSION=3.18.1
DIR_NAME=valgrind-${VALGRIND_VERSION}
ARCHIVE_NAME=${DIR_NAME}.tar.bz2
PREFIX="${TARGET_DIR}/${DIR_NAME}"

# Increase this to enforce a recreation of the build cache
BUILD_ID=0

build_package() {
    mkdir -p "$TARGET_DIR/src"
    cd "$TARGET_DIR/src"

    # Get the sources from nexus or upstream
    mirrored_download "${ARCHIVE_NAME}" "https://sourceware.org/pub/valgrind/${ARCHIVE_NAME}"

    tar xf "${ARCHIVE_NAME}"
    cd "$DIR_NAME"
    ./autogen.sh
    ./configure --prefix="${PREFIX}"
    make -j4
    make install

    cd "$TARGET_DIR"
    rm -rf "$TARGET_DIR/src"
}

test_package() {
    log "Testing for valgrind $VALGRIND_VERSION in \$PATH"
    valgrind --version | grep "^valgrind-$VALGRIND_VERSION$" >/dev/null 2>&1 || (
        echo "Invalid valgrind version: $(valgrind --version)"
        exit 1
    )
}

cached_build "${TARGET_DIR}" "${DIR_NAME}" "${BUILD_ID}" "${DISTRO}" "${BRANCH_VERSION}"
set_bin_symlinks "${TARGET_DIR}" "${DIR_NAME}"
test_package
