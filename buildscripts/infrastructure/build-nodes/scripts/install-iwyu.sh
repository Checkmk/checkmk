#!/bin/bash
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

set -e -o pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" >/dev/null 2>&1 && pwd)"
# shellcheck source=buildscripts/infrastructure/build-nodes/scripts/build_lib.sh
. "${SCRIPT_DIR}/build_lib.sh"

INSTALL_PREFIX=""
CLANG_VERSION=""
TARGET_DIR="${TARGET_DIR:-/opt}"

# option parsing ###############################################################

if ! OPTIONS=$(getopt -o 'c:u' --long 'clang-version:,user' -n "$(basename "$0")" -- "$@"); then
    failure "error parsing options"
fi
eval set -- "$OPTIONS"
unset OPTIONS

while true; do
    case "$1" in
        '-u' | '--user')
            INSTALL_PREFIX="${HOME}/.local"
            shift
            continue
            ;;
        '-c' | '--clang-version')
            CLANG_VERSION="$2"
            shift 2
            continue
            ;;
        '--')
            shift
            break
            ;;
        *) failure "internal error" ;;
    esac
done

# option validation ############################################################

if [[ $# -ne 0 ]]; then
    failure "superfluous arguments:" "$@"
fi

if [ -z "$CLANG_VERSION" ]; then
    CLANG_VERSION=$(get_version "$SCRIPT_DIR" CLANG_VERSION)
fi

# The tag/version numbering scheme is a big mess...
case $CLANG_VERSION in
    7) TAG_NAME="7.0" LIB_VERSION="7" ;;
    8) TAG_NAME="8.0" LIB_VERSION="8" ;;
    9) TAG_NAME="9.0" LIB_VERSION="9" ;;
    *) TAG_NAME="${CLANG_VERSION}" LIB_VERSION="${CLANG_VERSION}" ;;
esac

CLANG_LIB_PATH=/usr/lib/llvm-${LIB_VERSION}
if [[ ! -d ${CLANG_LIB_PATH} ]]; then
    failure "Clang ${CLANG_VERSION} is not installed."
fi

if [[ -n ${INSTALL_PREFIX} ]]; then
    INSTALLATION_MODE=locally
else
    INSTALLATION_MODE=globally
fi
echo "IWYU (Clang ${CLANG_VERSION} version) will be installed ${INSTALLATION_MODE}."

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
    --branch "clang_${TAG_NAME}" \
    https://github.com/include-what-you-use/include-what-you-use

IWYU_VERSION=$(grep --word-regexp IWYU_VERSION_STRING include-what-you-use/iwyu_version.h | sed 's/^.*"\(.*\)"$/\1/')
IWYU_PATH=/opt/iwyu-${IWYU_VERSION}

mkdir -p include-what-you-use-build
cd include-what-you-use-build
cmake -Wno-dev \
    -G "Unix Makefiles" \
    -DCMAKE_BUILD_TYPE=Release \
    -DCMAKE_PREFIX_PATH="${CLANG_LIB_PATH}" \
    -DCMAKE_INSTALL_PREFIX="${INSTALL_PREFIX}${IWYU_PATH}" \
    ../include-what-you-use
make -j8 install

cd "${INSTALL_PREFIX}${IWYU_PATH}/bin"
ln --symbolic --force include-what-you-use iwyu
ln --symbolic --force iwyu_tool.py iwyu_tool

if [[ -n ${INSTALL_PREFIX} ]]; then
    mkdir -p "${INSTALL_PREFIX}/bin"
    cd "${INSTALL_PREFIX}/bin"
    ln --symbolic --force "..${IWYU_PATH}/bin/"* .
else
    mkdir -p "$(dirname "${IWYU_PATH}")"
    cd "$(dirname "${IWYU_PATH}")"
    rm -f iwyu
    ln --symbolic --force "$(basename "${IWYU_PATH}")" iwyu

    # Hack for our containers
    echo "Set symlink"
    mkdir -p "${TARGET_DIR}/bin"
    ln -sf "${IWYU_PATH}/bin/"* "${TARGET_DIR}/bin"
fi
