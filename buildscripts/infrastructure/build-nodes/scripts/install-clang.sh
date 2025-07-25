#!/bin/bash
################################################################################
# Part of the LLVM Project, under the Apache License v2.0 with LLVM Exceptions.
# See https://llvm.org/LICENSE.txt for license information.
# SPDX-License-Identifier: Apache-2.0 WITH LLVM-exception
################################################################################
#
# This script will install the llvm toolchain on the different
# Debian and Ubuntu versions

set -eu

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" >/dev/null 2>&1 && pwd)"
# shellcheck source=buildscripts/infrastructure/build-nodes/scripts/build_lib.sh
. "${SCRIPT_DIR}/build_lib.sh"

# read optional command line argument
if [ "$#" -eq 1 ]; then
    CLANG_VERSION=$1
else
    CLANG_VERSION=$(get_version "$SCRIPT_DIR" CLANG_VERSION)
fi

DISTRO=$(lsb_release -is)
VERSION=$(lsb_release -sr)
DIST_VERSION="${DISTRO}_${VERSION}"

if [[ $EUID -ne 0 ]]; then
    failure "This script must be run as root!"
fi

declare -A CLANG_VERSION_PATTERNS
CLANG_VERSION_PATTERNS[9]="-9"
CLANG_VERSION_PATTERNS[10]="-10"
CLANG_VERSION_PATTERNS[11]="-11"
CLANG_VERSION_PATTERNS[12]="-12"
CLANG_VERSION_PATTERNS[13]="-13"
CLANG_VERSION_PATTERNS[14]="-14"
CLANG_VERSION_PATTERNS[15]="-15"
CLANG_VERSION_PATTERNS[16]="-16"
CLANG_VERSION_PATTERNS[17]="-17"
CLANG_VERSION_PATTERNS[18]="-18"
CLANG_VERSION_PATTERNS[19]="-19"
CLANG_VERSION_PATTERNS[20]="-20"

if [ ! ${CLANG_VERSION_PATTERNS[$CLANG_VERSION]+_} ]; then
    failure "This script does not support LLVM version $CLANG_VERSION"
fi

CLANG_VERSION_STRING=${CLANG_VERSION_PATTERNS[$CLANG_VERSION]}

# find the right repository name for the distro and version
case "$DIST_VERSION" in
    Debian_unstable) REPO_NAME="deb http://apt.llvm.org/unstable/ llvm-toolchain$CLANG_VERSION_STRING main" ;;
    Debian_testing) REPO_NAME="deb http://apt.llvm.org/unstable/ llvm-toolchain$CLANG_VERSION_STRING main" ;;
    Ubuntu_22.04) REPO_NAME="deb http://apt.llvm.org/jammy/ llvm-toolchain-jammy$CLANG_VERSION_STRING main" ;;
    Ubuntu_24.04) REPO_NAME="deb http://apt.llvm.org/noble/ llvm-toolchain-noble$CLANG_VERSION_STRING main" ;;
    Ubuntu_24.10) REPO_NAME="deb http://apt.llvm.org/oracular/ llvm-toolchain-oracular$CLANG_VERSION_STRING main" ;;
    *) failure "Distribution '$DISTRO' in version '$VERSION' is not supported by this script (${DIST_VERSION})." >&2 ;;
esac

# install everything
wget -O - https://apt.llvm.org/llvm-snapshot.gpg.key | apt-key add -
if [[ -e "/etc/apt/sources.list.d/clang.list" ]]; then
    if ! grep -Fxq "${REPO_NAME}" /etc/apt/sources.list.d/clang.list; then
        echo "${REPO_NAME}" >/etc/apt/sources.list.d/clang.list
    fi
else
    echo "${REPO_NAME}" >>/etc/apt/sources.list.d/clang.list
fi
apt-get update
apt-get install -y \
    "clang-$CLANG_VERSION" \
    "clangd-$CLANG_VERSION" \
    "clang-format-$CLANG_VERSION" \
    "clang-tidy-$CLANG_VERSION" \
    "lld-$CLANG_VERSION" \
    "lldb-$CLANG_VERSION" \
    "libclang-$CLANG_VERSION-dev"

# Workaround for https://github.com/llvm/llvm-project/issues/61550
if [ "$CLANG_VERSION" = 16 ]; then
    (cd /usr/lib/llvm-16/lib/clang && ln -s 16 16.0.0)
fi

"${SCRIPT_DIR}/install-iwyu.sh" --clang-version="$CLANG_VERSION"
