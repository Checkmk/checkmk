#!/bin/bash
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

set -e -o pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" >/dev/null 2>&1 && pwd)"
# shellcheck source=buildscripts/infrastructure/build-nodes/scripts/build_lib.sh
. "${SCRIPT_DIR}/build_lib.sh"

VERSION="0.14.3"
INSTALL_PREFIX=/opt/patchelf-${VERSION}

# temporary directory handling #################################################

WORK_DIR=$(mktemp --directory)
if [[ -z ${WORK_DIR} || ! -d ${WORK_DIR} ]]; then
    failure "could not create temporary working directory"
fi

cleanup() {
    rm -rf "${WORK_DIR}"
    echo "deleted temporary working directory ${WORK_DIR}"
}
trap cleanup EXIT

# build/install ################################################################

cd "${WORK_DIR}"
git clone \
    --depth 1 \
    --branch ${VERSION} \
    https://github.com/NixOS/patchelf.git

cd patchelf
echo "$PWD"
./bootstrap.sh
./configure --prefix=${INSTALL_PREFIX}
make -j8 install

ln -sf "${INSTALL_PREFIX}/bin/"* /usr/bin

test_package "patchelf --version" "patchelf $VERSION$"
