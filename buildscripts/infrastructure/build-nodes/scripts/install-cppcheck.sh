#!/bin/bash
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

set -e

INSTALL_PREFIX=""
CPPCHECK_VERSION=1.90

failure() {
    echo "$(basename $0):" "$@" >&2
    exit 1
}

# option parsing ###############################################################

OPTIONS=$(getopt -o 'c:u' --long 'cppcheck-version:,user' -n "$(basename $0)" -- "$@")
if [[ $? -ne 0 ]]; then
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
    '-c' | '--cppcheck-version')
        CPPCHECK_VERSION="$2"
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

if [[ -n ${INSTALL_PREFIX} ]]; then
    INSTALLATION_MODE=locally
else
    INSTALLATION_MODE=globally
fi
echo "Cppcheck (version ${CPPCHECK_VERSION}) will be installed ${INSTALLATION_MODE}."

# temporary directory handling #################################################

WORK_DIR=$(mktemp --directory)
if [[ -z ${WORK_DIR} || ! -d ${WORK_DIR} ]]; then
    failure "could not create temporary working directory"
fi

cleanup() {
    rm -rf ${WORK_DIR}
    echo "deleted temporary working directory ${WORK_DIR}"
}
trap cleanup EXIT

# build/install ################################################################

cd ${WORK_DIR}
git -c advice.detachedHead=false clone \
    --depth 1 \
    --branch ${CPPCHECK_VERSION} \
    https://github.com/danmar/cppcheck.git
CPPCHECK_PATH="/opt/cppcheck-${CPPCHECK_VERSION}"

mkdir -p cppcheck-build
cd cppcheck-build
cmake -G "Unix Makefiles" \
    -DCMAKE_BUILD_TYPE=Release \
    -DHAVE_RULES=ON \
    -DUSE_MATCHCOMPILER=ON \
    -DCMAKE_INSTALL_PREFIX=${INSTALL_PREFIX}${CPPCHECK_PATH} \
    ../cppcheck
make -j8 install

if [[ -n ${INSTALL_PREFIX} ]]; then
    mkdir -p ${INSTALL_PREFIX}/bin
    cd ${INSTALL_PREFIX}/bin
    ln --symbolic --force ..${CPPCHECK_PATH}/bin/* .
else
    mkdir -p $(dirname ${CPPCHECK_PATH})
    cd $(dirname ${CPPCHECK_PATH})
    rm -f cppcheck
    ln --symbolic --force $(basename ${CPPCHECK_PATH}) cppcheck
fi
