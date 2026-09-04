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
GDB_TARBALL_NAME="${TARGET}-gdb.tar.xz"

# Deliberately independent of the Bazel module's own cmk.N counter
# (gcc_toolchain/<version>/): that tracks registry publishes, not
# toolchain builds.
# defconfig lines are sorted (order-independent); Dockerfile lines are
# not (instruction order matters).
_TOOLCHAIN_HASH_INPUT="$(mktemp)"
{
    grep -vE '^[[:space:]]*(#|$)' "${GCC_TOOLCHAIN_DIR}/${TARGET}.defconfig" | sort
    grep -vE '^[[:space:]]*(#|$)' "${GCC_TOOLCHAIN_DIR}/docker/Dockerfile"
} >"${_TOOLCHAIN_HASH_INPUT}"
INTERNAL_VERSION="$(sha256sum "${_TOOLCHAIN_HASH_INPUT}" | cut -c1-8)"
# Delete synchronously, not via trap: a sourced file's EXIT trap would
# be silently replaced by the caller's (e.g. test.sh's).
rm -f "${_TOOLCHAIN_HASH_INPUT}"
TOOLCHAIN_VERSION="gcc${GCC_VERSION}-glibc${GLIBC_VERSION}-${INTERNAL_VERSION}"
