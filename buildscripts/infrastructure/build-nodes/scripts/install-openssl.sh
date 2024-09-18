#!/bin/bash
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

set -e -o pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" >/dev/null 2>&1 && pwd)"
# shellcheck source=buildscripts/infrastructure/build-nodes/scripts/build_lib.sh
. "${SCRIPT_DIR}/build_lib.sh"

OPENSSL_VERSION=3.0.14
DIR_NAME=openssl-${OPENSSL_VERSION}
ARCHIVE_NAME=${DIR_NAME}.tar.gz
TARGET_DIR="${TARGET_DIR:-/opt}"
TARGET="" # for x64, use the default target

# OpenSSL "config" seems to have problems with detecting 32bit architecture in some cases
[ "${ARCHITECTURE}" = i386 ] && TARGET="linux-x86"
# Increase this to enforce a recreation of the build cache
BUILD_ID=10

build_package() {
    mkdir -p "$TARGET_DIR/src"
    cd "$TARGET_DIR/src"

    # Get the sources from nexus or upstream
    mirrored_download "${ARCHIVE_NAME}" "https://www.openssl.org/source/openssl-${OPENSSL_VERSION}.tar.gz"

    # Now build the package
    tar xf "${ARCHIVE_NAME}"
    cd "${DIR_NAME}"
    ./config "${TARGET}" --libdir=lib --prefix="${TARGET_DIR}/${DIR_NAME}" enable-md2 -Wl,-rpath,"${TARGET_DIR}/${DIR_NAME}"/lib
    make -j6
    make install

    cd "$TARGET_DIR"
    rm -rf "$TARGET_DIR/src"
}

cached_build "${TARGET_DIR}" "${DIR_NAME}" "${BUILD_ID}" "${DISTRO}" "${BRANCH_VERSION}"

test_package "${TARGET_DIR}/${DIR_NAME}/bin/openssl version" "^OpenSSL $OPENSSL_VERSION"
