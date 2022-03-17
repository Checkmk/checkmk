#!/bin/bash
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

set -e -o pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" >/dev/null 2>&1 && pwd)"
. "${SCRIPT_DIR}/build_lib.sh"

OPENSSL_VERSION=1.1.1n
DIR_NAME=openssl-${OPENSSL_VERSION}
ARCHIVE_NAME=${DIR_NAME}.tar.gz
TARGET_DIR=/opt

# Increase this to enforce a recreation of the build cache
BUILD_ID=1

build_package() {
    mkdir -p /opt/src
    cd /opt/src

    # Get the sources from nexus or upstream
    mirrored_download "${ARCHIVE_NAME}" "https://www.openssl.org/source/openssl-${OPENSSL_VERSION}.tar.gz"

    # Now build the package
    tar xf "${ARCHIVE_NAME}"
    cd "${DIR_NAME}"
    ./config --prefix="${TARGET_DIR}/${DIR_NAME}" enable-md2 -Wl,-rpath,/opt/"${DIR_NAME}"/lib
    make -j6
    make install

    cd /opt
    rm -rf /opt/src
}

cached_build "${TARGET_DIR}" "${DIR_NAME}" "${BUILD_ID}" "${DISTRO}" "${BRANCH_VERSION}"
