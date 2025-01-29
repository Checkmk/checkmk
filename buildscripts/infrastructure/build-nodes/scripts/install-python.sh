#!/bin/bash
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

set -e -o pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" >/dev/null 2>&1 && pwd)"
# shellcheck source=buildscripts/infrastructure/build-nodes/scripts/build_lib.sh
. "${SCRIPT_DIR}/build_lib.sh"

# read optional command line argument
if [ "$#" -eq 1 ]; then
    PYTHON_VERSION=$1
else
    PYTHON_VERSION=$(get_version "$SCRIPT_DIR" PYTHON_VERSION)
fi

TARGET_DIR="${TARGET_DIR:-/opt}"
OPENSSL_VERSION=3.0.14
OPENSSL_PATH="${TARGET_DIR}/openssl-${OPENSSL_VERSION}"
DIR_NAME=Python-${PYTHON_VERSION}
ARCHIVE_NAME=${DIR_NAME}.tgz

# Increase the numeric suffix to enforce a recreation of the build cache
BUILD_ID="openssl-${OPENSSL_VERSION}-11"

build_package() {
    mkdir -p "$TARGET_DIR/src"
    cd "$TARGET_DIR/src"

    # Get the sources from nexus or upstream
    mirrored_download "${ARCHIVE_NAME}" "https://www.python.org/ftp/python/${PYTHON_VERSION}/${ARCHIVE_NAME}"

    # Now build the package
    tar xf "${ARCHIVE_NAME}"
    cd "${DIR_NAME}"
    LD_LIBRARY_PATH="${OPENSSL_PATH}/lib" \
        LDFLAGS="-Wl,--rpath,${TARGET_DIR}/${DIR_NAME}/lib -Wl,--rpath,${OPENSSL_PATH}/lib -L${OPENSSL_PATH}/lib" \
        ./configure \
        --prefix="${TARGET_DIR}/${DIR_NAME}" \
        --with-ensurepip=install \
        --with-openssl="${OPENSSL_PATH}" \
        --enable-optimizations \
        --with-lto \
        --enable-shared
    make -j2
    make install

    cd "$TARGET_DIR"
    rm -rf "$TARGET_DIR/src"
}

if [ "$1" != "link-only" ]; then
    cached_build "${TARGET_DIR}" "${DIR_NAME}" "${BUILD_ID}" "${DISTRO}" "${BRANCH_VERSION}"
    test_package "${TARGET_DIR}/${DIR_NAME}/bin/python3 --version" "Python $PYTHON_VERSION"
fi
set_bin_symlinks "${TARGET_DIR}" "${DIR_NAME}"

test_package "${TARGET_DIR}/bin/python3 --version" "Python $(get_version "$SCRIPT_DIR" PYTHON_VERSION)"
