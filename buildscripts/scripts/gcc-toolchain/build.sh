#!/bin/bash
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
set -e -o pipefail

# shellcheck source=buildscripts/scripts/gcc-toolchain/common.sh
. "$(dirname "${BASH_SOURCE[0]}")/common.sh"

IMAGE="gcc-toolchain-builder"

usage() {
    echo "Usage: $0 <output-dir>" >&2
    exit 1
}

build_image() {
    docker build -t "${IMAGE}" "${GCC_TOOLCHAIN_DIR}/docker"
}

build_toolchain() {
    local output_dir="$1"
    docker run --rm \
        -v "${GCC_TOOLCHAIN_DIR}/${TARGET}.defconfig:/input/defconfig:ro" \
        -v "${GCC_TOOLCHAIN_DIR}/docker/build.sh:/input/build.sh:ro" \
        -v "${output_dir}:/output" \
        -e "TARGET=${TARGET}" \
        -e "TARBALL_NAME=${TARBALL_NAME}" \
        -e "GDB_TARBALL_NAME=${GDB_TARBALL_NAME}" \
        "${IMAGE}" bash /input/build.sh
}

main() {
    [ $# -eq 1 ] || usage
    local output_dir="$1"
    mkdir -p "${output_dir}"
    output_dir="$(readlink -e "${output_dir}")"

    build_image
    build_toolchain "${output_dir}"

    echo "Toolchain tarball: ${output_dir}/${TARBALL_NAME}"
    echo "gdb tarball: ${output_dir}/${GDB_TARBALL_NAME}"
}

main "$@"
