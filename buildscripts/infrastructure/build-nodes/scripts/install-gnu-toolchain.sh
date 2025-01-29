#!/bin/bash
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
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
GCC_ARCHIVE_NAME="gcc-${GCC_VERSION}.tar.gz"
GCC_URL="${MIRROR_URL}gcc/gcc-${GCC_VERSION}/${GCC_ARCHIVE_NAME}"

BINUTILS_VERSION="2.41"
BINUTILS_ARCHIVE_NAME="binutils-${BINUTILS_VERSION}.tar.gz"
BINUTILS_URL="${MIRROR_URL}binutils/${BINUTILS_ARCHIVE_NAME}"

DIR_NAME=gcc-${GCC_VERSION}
TARGET_DIR="${TARGET_DIR:-/opt}"
PREFIX=${TARGET_DIR}/${DIR_NAME}
BUILD_DIR="${TARGET_DIR}/src"

# Increase this to enforce a recreation of the build cache
BUILD_ID="${BINUTILS_VERSION}-1"

download_sources() {
    # Get the sources from nexus or upstream
    mirrored_download "${BINUTILS_ARCHIVE_NAME}" "${BINUTILS_URL}"
    mirrored_download "${GCC_ARCHIVE_NAME}" "${GCC_URL}"

    # Some GCC dependency download optimization
    local FILE_NAME="gcc-${GCC_VERSION}-with-prerequisites.tar.gz"
    local MIRROR_BASE_URL=${NEXUS_ARCHIVES_URL}
    local MIRROR_URL=${MIRROR_BASE_URL}$FILE_NAME
    local MIRROR_CREDENTIALS="${NEXUS_USERNAME}:${NEXUS_PASSWORD}"
    if ! _download_from_mirror "${FILE_NAME}" "${MIRROR_URL}" "${MIRROR_CREDENTIALS}"; then
        log "File not available from ${MIRROR_URL}, creating"

        tar xzf "${GCC_ARCHIVE_NAME}"
        (cd "gcc-${GCC_VERSION}" && ./contrib/download_prerequisites)
        tar czf "${FILE_NAME}" "gcc-${GCC_VERSION}"

        _upload_to_mirror "${FILE_NAME}" "${MIRROR_BASE_URL}" "${MIRROR_CREDENTIALS}"
    fi
}

build_binutils() {
    log "Build binutils-${BINUTILS_VERSION}"
    cd "${BUILD_DIR}"
    tar xzf binutils-${BINUTILS_VERSION}.tar.gz
    # remove potential older build directories
    if [[ -d binutils-${BINUTILS_VERSION}-build ]]; then
        rm -rf "binutils-${BINUTILS_VERSION}-build"
    fi
    mkdir binutils-${BINUTILS_VERSION}-build
    cd binutils-${BINUTILS_VERSION}-build
    # sles-12* had (we don't build it anymore anyways) ancient makeinfo versions, so let's just skip
    # info generation for all distros, we don't really need it.
    MAKEINFO=true ../binutils-${BINUTILS_VERSION}/configure \
        --prefix="${PREFIX}"
    make -j4 MAKEINFO=true
    make install MAKEINFO=true
}

build_gcc() {
    log "Build gcc-${GCC_VERSION}"
    cd "${BUILD_DIR}"
    tar xzf "gcc-${GCC_VERSION}-with-prerequisites.tar.gz"
    # remove potential older build directories
    if [[ -d gcc-${GCC_VERSION}-build ]]; then
        rm -rf "gcc-${GCC_VERSION}-build"
    fi
    mkdir "gcc-${GCC_VERSION}-build"
    cd "gcc-${GCC_VERSION}-build"
    "../gcc-${GCC_VERSION}/configure" \
        --prefix="${PREFIX}" \
        --program-suffix=-"${GCC_MAJOR}" \
        --enable-linker-build-id \
        --disable-multilib \
        --enable-languages=c,c++
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
    ln -sf "${PREFIX}/bin/gcc-${GCC_MAJOR}" "${TARGET_DIR}"/bin/gcc
    ln -sf "${PREFIX}/bin/g++-${GCC_MAJOR}" "${TARGET_DIR}"/bin/g++

    # Save distro executables under [name]-orig. It is used by some build steps
    # later that need to use the distro original compiler. For some platforms
    # we need this to fix the libstdc++ dependency (e.g. protobuf, grpc)
    [ -e /usr/bin/gcc ] && mv /usr/bin/gcc /usr/bin/gcc-orig
    [ -e /usr/bin/g++ ] && mv /usr/bin/g++ /usr/bin/g++-orig

    ln -sf "${PREFIX}/bin/"* /usr/bin
    ln -sf "${PREFIX}/bin/gcc-${GCC_MAJOR}" /usr/bin/gcc
    ln -sf "${PREFIX}/bin/g++-${GCC_MAJOR}" /usr/bin/g++

    # not really a symlink, but almost...
    echo "${PREFIX}/lib64" >"/etc/ld.so.conf.d/gcc-${GCC_VERSION}.conf"
    ldconfig
}

build_package() {
    mkdir -p "$TARGET_DIR/src"
    cd "$TARGET_DIR/src"

    download_sources
    build_binutils
    build_gcc

    cd "$TARGET_DIR"
    rm -rf "$TARGET_DIR/src"
}

test_packages() {
    for i in $(dpkg -L binutils | grep '/bin/'); do
        this_version=$($i --version)
        if [[ "$this_version" == *"Binutils)"* ]]; then
            echo "$this_version" | grep -q "${BINUTILS_VERSION}" >/dev/null 2>&1 || (
                echo "Invalid version: ${i}: ${this_version}!=${BINUTILS_VERSION}"
                exit 1
            )
        else
            echo "${i} not of interest"
            # e.g. /usr/bin/dwp would report "GNU dwp (GNU Binutils for Ubuntu) 2.34"
        fi
    done
}

if [ "$1" != "link-only" ]; then
    cached_build "${TARGET_DIR}" "${DIR_NAME}" "${BUILD_ID}" "${DISTRO}" "${BRANCH_VERSION}"
fi
set_symlinks

test_packages
test_package "/usr/bin/gcc --version" "$GCC_VERSION"
