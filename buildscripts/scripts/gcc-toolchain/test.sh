#!/bin/bash
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
set -e -o pipefail

# shellcheck source=buildscripts/scripts/gcc-toolchain/common.sh
. "$(dirname "${BASH_SOURCE[0]}")/common.sh"

usage() {
    echo "Usage: $0 <tarball>" >&2
    exit 1
}

compile_hello_world() {
    local tarball_dir="$1" tarball_name="$2" work_dir="$3"
    docker run --rm \
        -v "${tarball_dir}:/input:ro" \
        -v "${GCC_TOOLCHAIN_DIR}/docker/test.sh:/input-script/test.sh:ro" \
        -v "${work_dir}:/output" \
        -e "TARGET=${TARGET}" \
        -e "TARBALL_NAME=${tarball_name}" \
        ubuntu:24.04 bash /input-script/test.sh
}

run_smoke_test() {
    local work_dir="$1"
    local almalinux_8_image
    almalinux_8_image="$("${REPO_ROOT}/buildscripts/docker_image_aliases/resolve.py" IMAGE_ALMALINUX_8)"
    docker run --rm -v "${work_dir}:/output:ro" "${almalinux_8_image}" \
        sh -c '/output/hello_c && /output/hello_cpp && echo "smoke test passed"'
}

main() {
    [ $# -eq 1 ] || usage
    local tarball tarball_dir tarball_name work_dir
    tarball="$(readlink -e "$1")"
    tarball_dir="$(dirname "${tarball}")"
    tarball_name="$(basename "${tarball}")"
    work_dir="$(mktemp -d)"
    trap 'rm -rf "${work_dir}"' EXIT

    compile_hello_world "${tarball_dir}" "${tarball_name}" "${work_dir}"
    run_smoke_test "${work_dir}"
}

main "$@"
