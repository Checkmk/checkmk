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

TARGET_DIR="${TARGET_DIR:-/opt}"
DIR_NAME="bin"
TAPLO_VERSION="0.9.3"
TAPLO_GZ="taplo-full-linux-x86.gz"

mkdir -p "${TARGET_DIR}/${DIR_NAME}"
cd "${TARGET_DIR}/${DIR_NAME}"
wget "https://github.com/tamasfe/taplo/releases/download/${TAPLO_VERSION}/${TAPLO_GZ}"

gzip -d "${TAPLO_GZ}"
mv taplo-full-linux-x86 taplo
chmod +x taplo

test_package "taplo --version" "${TAPLO_VERSION}"
