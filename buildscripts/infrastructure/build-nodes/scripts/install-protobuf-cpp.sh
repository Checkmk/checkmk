#!/bin/bash
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

set -e -o pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" >/dev/null 2>&1 && pwd)"
# shellcheck source=buildscripts/infrastructure/build-nodes/scripts/build_lib.sh
. "${SCRIPT_DIR}/build_lib.sh"

PROTOBUF_VERSION=3.18.1
PACKAGE_NAME=protobuf-cpp
DIR_NAME=protobuf-${PROTOBUF_VERSION}
ARCHIVE_NAME=${PACKAGE_NAME}-${PROTOBUF_VERSION}.tar.gz

# Increase this to enforce a recreation of the build cache
BUILD_ID=1

INSTALL_PREFIX=
TARGET_DIR=/opt
USE_BUILD_CACHE=1
VERIFY_INSTALL=1

# option parsing ###############################################################

if ! OPTIONS=$(getopt -o us --long user,system -- "$@"); then
    echo "error parsing options"
    exit 1
fi
eval set -- "$OPTIONS"
unset OPTIONS
while true; do
    case "$1" in
        '-u' | '--user')
            INSTALL_PREFIX="${HOME}/.local"
            TARGET_DIR=${INSTALL_PREFIX}${TARGET_DIR}
            USE_BUILD_CACHE=
            break
            ;;
        '-s' | '--system')
            USE_BUILD_CACHE=
            break
            ;;
        '--')
            shift
            break
            ;;
        *)
            echo "internal error"
            exit 1
            ;;
    esac
done

# build/install ################################################################

build_package() {
    mkdir -p "$TARGET_DIR/src"
    cd "$TARGET_DIR/src"

    if [ -n "$USE_BUILD_CACHE" ]; then
        mirrored_download "${ARCHIVE_NAME}" "https://github.com/protocolbuffers/protobuf/releases/download/v${PROTOBUF_VERSION}/${ARCHIVE_NAME}"
    else
        wget -O "${ARCHIVE_NAME}" "https://github.com/protocolbuffers/protobuf/releases/download/v${PROTOBUF_VERSION}/${ARCHIVE_NAME}"
    fi

    # Now build the package
    tar xf "${ARCHIVE_NAME}"
    cd "${DIR_NAME}"
    ./configure --prefix="${TARGET_DIR}/${DIR_NAME}"
    make -j6
    make install

    cd "$TARGET_DIR"
    rm -rf "$TARGET_DIR/src"
}

install() {
    mkdir -p "${INSTALL_PREFIX}/usr/bin"
    ln -sf "${TARGET_DIR}/${DIR_NAME}/bin/"* "${INSTALL_PREFIX}/usr/bin/"

    if [[ -n "${INSTALL_PREFIX}" ]]; then
        # The method is by definition not consistent, still it is good enough for development locally.
        mkdir -p "${INSTALL_PREFIX}/bin"
        ln -sf "${TARGET_DIR}/${DIR_NAME}/bin/"* "${INSTALL_PREFIX}/bin/"
    fi

    mkdir -p "${INSTALL_PREFIX}/usr/include"
    cp -prl "${TARGET_DIR}/${DIR_NAME}/include/"* "${INSTALL_PREFIX}/usr/include"

    if [ -d "${INSTALL_PREFIX}/usr/lib64/pkgconfig" ]; then
        PKGCONFIG_DIR=${INSTALL_PREFIX}/usr/lib64/pkgconfig
    else
        PKGCONFIG_DIR=${INSTALL_PREFIX}/usr/lib/pkgconfig
    fi

    mkdir -p "${PKGCONFIG_DIR}"
    cp -prl "${TARGET_DIR}/${DIR_NAME}/lib/pkgconfig/"*.pc "${PKGCONFIG_DIR}"
}

verify_install() {
    if [ -z "$VERIFY_INSTALL" ]; then
        return
    fi

    if ! type protoc >/dev/null 2>&1; then
        echo "ERROR: protoc not in $PATH"
        exit 1
    fi

    protoc --version
    if [ "$(protoc --version)" != "libprotoc ${PROTOBUF_VERSION}" ]; then
        echo "ERROR: protoc version invalid (expected ${PROTOBUF_VERSION})"
        exit 1
    fi

    if [ -d "$INSTALL_PREFIX" ]; then
        # Based on https://autotools.io/
        export PKG_CONFIG_PATH=$INSTALL_PREFIX/usr/lib/pkgconfig
        export PKG_CONFIG_LIBDIR=$INSTALL_PREFIX/usr/lib/pkgconfig
    fi

    pkg-config --cflags protobuf
    pkg-config --libs protobuf
}

if [ -n "$USE_BUILD_CACHE" ]; then
    # Get the sources from nexus or upstream
    cached_build "${TARGET_DIR}" "${DIR_NAME}" "${BUILD_ID}" "${DISTRO}" "${BRANCH_VERSION}"
else
    build_package
fi
install
verify_install
