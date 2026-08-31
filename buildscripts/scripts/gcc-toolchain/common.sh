#!/bin/bash
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# BASH_SOURCE, not $0 or git rev-parse: resolves correctly however this is invoked.
REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../../.." && pwd)"
GCC_TOOLCHAIN_DIR="${REPO_ROOT}/buildscripts/scripts/gcc-toolchain"

TARGET="x86_64-checkmk-linux-gnu"
GCC_VERSION="14.4.0"
GLIBC_VERSION="2.28"
TARBALL_NAME="${TARGET}-gcc${GCC_VERSION}-glibc${GLIBC_VERSION}.tar.xz"
