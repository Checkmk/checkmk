#!/bin/bash
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

set -e -o pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" >/dev/null 2>&1 && pwd)"
# shellcheck source=buildscripts/infrastructure/build-nodes/scripts/build_lib.sh
. "${SCRIPT_DIR}/build_lib.sh"

CMAKE_VERSION=3.21.1
DIR_NAME=cmake-${CMAKE_VERSION}-Linux-x86_64
ARCHIVE_NAME=${DIR_NAME}.tar.gz
TARGET_DIR=/opt

# Increase this to enforce a recreation of the build cache
BUILD_ID=1

build_package() {
    mkdir -p /opt
    cd /opt

    # Get the sources from nexus or upstream
    mirrored_download "${ARCHIVE_NAME}" "https://github.com/Kitware/CMake/releases/download/v${CMAKE_VERSION}/${ARCHIVE_NAME}"

    # TODO: Shouldn't we compile it on our own?
    tar xf "${ARCHIVE_NAME}"
    # NOTE: Upper/lower case seems to be mixed up in recent versions. :-/
    test ! -e "${DIR_NAME}" && mv "${DIR_NAME/-Linux-/-linux-}" "${DIR_NAME}"
}

cached_build "${TARGET_DIR}" "${DIR_NAME}" "${BUILD_ID}" "${DISTRO}" "${BRANCH_VERSION}"
ln -sf "${TARGET_DIR}/${DIR_NAME}/bin/"* /usr/bin/
