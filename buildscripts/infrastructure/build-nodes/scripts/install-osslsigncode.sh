#!/bin/bash
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

set -e -o pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" >/dev/null 2>&1 && pwd)"
# shellcheck source=buildscripts/infrastructure/build-nodes/scripts/build_lib.sh
. "${SCRIPT_DIR}/build_lib.sh"

VERSION="2.10"
INSTALL_PREFIX=/opt/osslsigncode-${VERSION}

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
    https://github.com/mtrojnar/osslsigncode.git

cd osslsigncode
echo "$PWD"
mkdir build && cd build && cmake -S .. -DCMAKE_INSTALL_PREFIX="${INSTALL_PREFIX}" && cmake --build . && cmake --install .

ln -sf "${INSTALL_PREFIX}/bin/"* /usr/bin

test_package "osslsigncode --version" "osslsigncode $VERSION"
