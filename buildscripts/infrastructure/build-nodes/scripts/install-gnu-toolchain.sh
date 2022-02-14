#!/bin/bash
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

set -e -o pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" >/dev/null 2>&1 && pwd)"
. "${SCRIPT_DIR}/build_lib.sh"

MIRROR_URL="https://ftp.gnu.org/gnu/"

GCC_MAJOR="11"
GCC_MINOR="2"
GCC_PATCHLEVEL="0"
GCC_VERSION="${GCC_MAJOR}.${GCC_MINOR}.${GCC_PATCHLEVEL}"
GCC_ARCHIVE_NAME="gcc-${GCC_VERSION}.tar.gz"
GCC_URL="${MIRROR_URL}gcc/gcc-${GCC_VERSION}/${GCC_ARCHIVE_NAME}"

BINUTILS_VERSION="2.36.1"
BINUTILS_ARCHIVE_NAME="binutils-${BINUTILS_VERSION}.tar.gz"
BINUTILS_URL="${MIRROR_URL}binutils/${BINUTILS_ARCHIVE_NAME}"

GDB_VERSION="11.1"
GDB_ARCHIVE_NAME="gdb-${GDB_VERSION}.tar.gz"
GDB_URL="${MIRROR_URL}gdb/${GDB_ARCHIVE_NAME}"

DIR_NAME=gcc-${GCC_VERSION}
TARGET_DIR=/opt
PREFIX=${TARGET_DIR}/${DIR_NAME}
BUILD_DIR=/opt/src

# Increase this to enforce a recreation of the build cache
BUILD_ID=1

download_sources() {
    # Get the sources from nexus or upstream
    mirrored_download "${BINUTILS_ARCHIVE_NAME}" "${BINUTILS_URL}"
    mirrored_download "${GCC_ARCHIVE_NAME}" "${GCC_URL}"
    mirrored_download "${GDB_ARCHIVE_NAME}" "${GDB_URL}"

    # Some GCC dependency download optimization
    local FILE_NAME="gcc-${GCC_VERSION}-with-prerequisites.tar.gz"
    local MIRROR_BASE_URL=${NEXUS_ARCHIVES_URL}
    local MIRROR_URL=${MIRROR_BASE_URL}$FILE_NAME
    local MIRROR_CREDENTIALS="${NEXUS_USERNAME}:${NEXUS_PASSWORD}"
    if ! _download_from_mirror "${FILE_NAME}" "${MIRROR_URL}"; then
        log "File not available from ${MIRROR_URL}, creating"

        tar xzf "${GCC_ARCHIVE_NAME}"
        (cd gcc-${GCC_VERSION} && ./contrib/download_prerequisites)
        tar czf ${FILE_NAME} gcc-${GCC_VERSION}

        _upload_to_mirror "${FILE_NAME}" "${MIRROR_BASE_URL}" "${MIRROR_CREDENTIALS}"
    fi
}

build_binutils() {
    log "Build binutils-${BINUTILS_VERSION}"
    cd ${BUILD_DIR}
    tar xzf binutils-${BINUTILS_VERSION}.tar.gz
    mkdir binutils-${BINUTILS_VERSION}-build
    cd binutils-${BINUTILS_VERSION}-build
    ../binutils-${BINUTILS_VERSION}/configure \
        --prefix=${PREFIX}
    make -j4
    make install
}

build_gcc() {
    log "Build gcc-${GCC_VERSION}"
    cd ${BUILD_DIR}
    tar xzf gcc-${GCC_VERSION}-with-prerequisites.tar.gz
    mkdir gcc-${GCC_VERSION}-build
    cd gcc-${GCC_VERSION}-build
    ../gcc-${GCC_VERSION}/configure \
        --prefix=${PREFIX} \
        --program-suffix=-${GCC_MAJOR} \
        --enable-linker-build-id \
        --disable-multilib \
        --enable-languages=c,c++
    make -j4
    make install
}

build_gdb() {
    log "Build gdb-${GDB_VERSION}"
    cd ${BUILD_DIR}
    tar xzf gdb-${GDB_VERSION}.tar.gz
    mkdir gdb-${GDB_VERSION}-build
    cd gdb-${GDB_VERSION}-build
    ../gdb-${GDB_VERSION}/configure \
        --prefix=${PREFIX} \
        CC=${PREFIX}/bin/gcc-${GCC_MAJOR} \
        CXX=${PREFIX}/bin/g++-${GCC_MAJOR} \
        "$(python -V 2>&1 | grep -q 'Python 2\.4\.' && echo "--with-python=no")"
    make -j4
    make install
}

set_symlinks() {
    log "Set symlink"

    # Save distro executables under [name]-orig. It is used by some build steps
    # later that need to use the distro original compiler. For some platforms
    # we need this to fix the libstdc++ dependency (e.g. protobuf, grpc)
    [ -e /usr/bin/gcc ] && mv /usr/bin/gcc /usr/bin/gcc-orig
    [ -e /usr/bin/g++ ] && mv /usr/bin/g++ /usr/bin/g++-orig

    ln -sf ${PREFIX}/bin/* /usr/bin
    ln -sf ${PREFIX}/bin/gcc-${GCC_MAJOR} /usr/bin/gcc
    ln -sf ${PREFIX}/bin/g++-${GCC_MAJOR} /usr/bin/g++

    # not really a symlink, but almost...
    echo ${PREFIX}/lib64 > /etc/ld.so.conf.d/gcc-${GCC_VERSION}.conf
    ldconfig
}

build_package() {
    mkdir -p /opt/src
    cd /opt/src

    download_sources
    build_binutils
    build_gcc
    build_gdb

    cd /opt
    rm -rf /opt/src
}

cached_build "${TARGET_DIR}" "${DIR_NAME}" "${BUILD_ID}" "${DISTRO}" "${BRANCH_VERSION}"
set_symlinks
