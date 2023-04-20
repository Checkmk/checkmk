#!/bin/bash
# Copyright (C) 2021 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# This will fetch and install bazel as described here:
# https://github.com/bazelbuild/bazel

set -e -o pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" >/dev/null 2>&1 && pwd)"

# provide common functions
# shellcheck source=buildscripts/infrastructure/build-nodes/scripts/build_lib.sh
. "${SCRIPT_DIR}/build_lib.sh"

DIR_NAME="bazel"
TARGET_DIR="/opt"
BAZEL_VERSION="$(<"${SCRIPT_DIR}"/.bazelversion)"
BAZEL_EXE_FILE="bazel-${BAZEL_VERSION}-linux-x86_64"

if [ "$1" != "link-only" ]; then
    mkdir -p "${TARGET_DIR}/${DIR_NAME}"
    cd "${TARGET_DIR}/${DIR_NAME}"
    mirrored_download \
        "${BAZEL_EXE_FILE}" \
        "https://github.com/bazelbuild/bazel/releases/download/${BAZEL_VERSION}/${BAZEL_EXE_FILE}"
    chmod +x "${BAZEL_EXE_FILE}"
fi

ln -s "${TARGET_DIR}/${DIR_NAME}/${BAZEL_EXE_FILE}" "/usr/bin/bazel"
