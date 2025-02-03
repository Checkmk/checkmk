#!/bin/bash
# Copyright (C) 2021 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# This will fetch and install bazel as described here:
# https://github.com/bazelbuild/bazel

set -e -o pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" >/dev/null 2>&1 && pwd)"
# shellcheck source=buildscripts/infrastructure/build-nodes/scripts/build_lib.sh
. "${SCRIPT_DIR}/build_lib.sh"

DIR_NAME="bazel"
TARGET_DIR="${TARGET_DIR:-/opt}"
BAZEL_VERSION="$(<"${SCRIPT_DIR}"/.bazelversion)"
BAZELISK_VERSION="v1.20.0"
BAZELISK_EXE_FILE="bazelisk-${BAZELISK_VERSION}-linux-amd64"
BAZELISK_EXE_FILE_WITHOUT_VERSION="bazelisk-linux-amd64"

if [ "$1" != "link-only" ]; then
    mkdir -p "${TARGET_DIR}/${DIR_NAME}"
    cd "${TARGET_DIR}/${DIR_NAME}"
    mirrored_download \
        "${BAZELISK_EXE_FILE}" \
        "https://github.com/bazelbuild/bazelisk/releases/download/${BAZELISK_VERSION}/${BAZELISK_EXE_FILE_WITHOUT_VERSION}"

    # see https://github.com/bazelbuild/bazelisk/issues/606
    if [[ -e ${BAZELISK_EXE_FILE_WITHOUT_VERSION} ]]; then
        mv ${BAZELISK_EXE_FILE_WITHOUT_VERSION} ${BAZELISK_EXE_FILE}
    fi
    chmod +x "${BAZELISK_EXE_FILE}"
fi

ln -sf "${TARGET_DIR}/${DIR_NAME}/${BAZELISK_EXE_FILE}" "/usr/bin/bazel"
# Let's also provide bazelisk in PATH, see https://github.com/bazelbuild/bazelisk?tab=readme-ov-file#installation
ln -sf "${TARGET_DIR}/${DIR_NAME}/${BAZELISK_EXE_FILE}" "/usr/bin/bazelisk"

export USE_BAZEL_VERSION=$BAZEL_VERSION
test_package "bazel --version" "^bazel $BAZEL_VERSION$"
