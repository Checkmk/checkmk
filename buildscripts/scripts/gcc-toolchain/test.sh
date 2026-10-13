#!/bin/bash
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
set -e -o pipefail

# shellcheck source=buildscripts/scripts/gcc-toolchain/common.sh
. "$(dirname "${BASH_SOURCE[0]}")/common.sh"

usage() {
    echo "Usage: $0 <output-dir>" >&2
    exit 1
}

stage_test_binaries() {
    local output_dir="$1" work_dir="$2"
    docker run --rm \
        -v "${output_dir}:/input:ro" \
        -v "${GCC_TOOLCHAIN_DIR}/docker/test.sh:/input-script/test.sh:ro" \
        -v "${work_dir}:/output" \
        -e "TARGET=${TARGET}" \
        -e "TARBALL_NAME=${TARBALL_NAME}" \
        -e "GDB_TARBALL_NAME=${GDB_TARBALL_NAME}" \
        ubuntu:24.04 bash /input-script/test.sh
}

run_smoke_test() {
    local work_dir="$1"
    local almalinux_8_image
    almalinux_8_image="$("${REPO_ROOT}/buildscripts/docker_image_aliases/resolve.py" IMAGE_ALMALINUX_8)"

    docker run --rm -v "${work_dir}:/output:ro" "${almalinux_8_image}" \
        sh -c '/output/hello_c && /output/hello_cpp && echo "smoke test passed"'

    if [ -f "${work_dir}/${TARGET}-gdb" ]; then
        docker run --rm -v "${work_dir}:/output:ro" "${almalinux_8_image}" \
            sh -c "/output/${TARGET}-gdb --version"
    fi
}

main() {
    [ $# -eq 1 ] || usage
    local output_dir work_dir
    output_dir="$(readlink -e "$1")"
    work_dir="$(mktemp -d)"
    trap 'rm -rf "${work_dir}"' EXIT

    stage_test_binaries "${output_dir}" "${work_dir}"
    run_smoke_test "${work_dir}"
}

main "$@"
