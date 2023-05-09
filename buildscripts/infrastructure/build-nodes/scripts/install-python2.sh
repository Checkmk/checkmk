#!/bin/bash
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

set -e -o pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" >/dev/null 2>&1 && pwd)"
. "${SCRIPT_DIR}/build_lib.sh"

PYTHON_VERSION=2.7.17
DIR_NAME=Python-${PYTHON_VERSION}
ARCHIVE_NAME=${DIR_NAME}.tgz
TARGET_DIR=/opt

# Increase this to enforce a recreation of the build cache
BUILD_ID=2

build_package() {
    mkdir -p /opt/src
    cd /opt/src

    # Get the sources from nexus or upstream
    mirrored_download "${ARCHIVE_NAME}" "https://www.python.org/ftp/python/${PYTHON_VERSION}/${ARCHIVE_NAME}"

    # Now build the package
    tar xf "${ARCHIVE_NAME}"
    cd "${DIR_NAME}"
    LDFLAGS="-Wl,--rpath,${TARGET_DIR}/${DIR_NAME}/lib" \
        ./configure \
        --prefix="${TARGET_DIR}/${DIR_NAME}" \
        --enable-unicode=ucs4 \
        --with-ensurepip=install \
        --enable-shared
    make -j2
    make install

    cd /opt
    rm -rf /opt/src
}

set_symlinks() {
    log "Set symlink"
    mkdir -p "${TARGET_DIR}/bin"
    ln -sf "${TARGET_DIR}/${DIR_NAME}/bin/"* "${TARGET_DIR}/bin"
}

cached_build "${TARGET_DIR}" "${DIR_NAME}" "${BUILD_ID}" "${DISTRO}" "${BRANCH_VERSION}"
set_symlinks
