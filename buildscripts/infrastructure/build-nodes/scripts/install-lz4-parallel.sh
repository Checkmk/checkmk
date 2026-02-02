#!/bin/bash
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# This will fetch and install lz4 as described here:
# https://github.com/lz4/lz4

set -e -o pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" >/dev/null 2>&1 && pwd)"
# shellcheck source=buildscripts/infrastructure/build-nodes/scripts/build_lib.sh
. "${SCRIPT_DIR}/build_lib.sh"

LZ4_VERSION="v1.10.0"
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
    --branch "$LZ4_VERSION" \
    https://github.com/lz4/lz4.git

cd lz4
make install

ln -sf /usr/local/bin/lz4 /usr/bin/lz4
test_package "/usr/local/bin/lz4 --version" "lz4 $LZ4_VERSION 64-bit multithread"
