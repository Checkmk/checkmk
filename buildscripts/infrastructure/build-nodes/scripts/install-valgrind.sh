#!/bin/bash
# Copyright (C) 2021 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

set -e -o pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" >/dev/null 2>&1 && pwd)"
# shellcheck source=buildscripts/infrastructure/build-nodes/scripts/build_lib.sh
. "${SCRIPT_DIR}/build_lib.sh"

TARGET_DIR="${TARGET_DIR:-/opt}"

VALGRIND_VERSION=3.19.0
DIR_NAME=valgrind-${VALGRIND_VERSION}
ARCHIVE_NAME=${DIR_NAME}.tar.bz2
PREFIX="${TARGET_DIR}/${DIR_NAME}"

# Increase this to enforce a recreation of the build cache
BUILD_ID=1

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

if [ "$1" != "link-only" ]; then
    cached_build "${TARGET_DIR}" "${DIR_NAME}" "${BUILD_ID}" "${DISTRO}" "${BRANCH_VERSION}"
fi
set_bin_symlinks "${TARGET_DIR}" "${DIR_NAME}"

test_package "${TARGET_DIR}/bin/valgrind --version" "^valgrind-$VALGRIND_VERSION$"
