#!/bin/bash
################################################################################
# Part of the LLVM Project, under the Apache License v2.0 with LLVM Exceptions.
# See https://llvm.org/LICENSE.txt for license information.
# SPDX-License-Identifier: Apache-2.0 WITH LLVM-exception
################################################################################
#
# This script will install the llvm toolchain on the different
# Debian and Ubuntu versions

set -eux

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" >/dev/null 2>&1 && pwd)"

failure() {
    echo "$(basename $0):" "$@" >&2
    exit 1
}

# read optional command line argument
if [ "$#" -eq 1 ]; then
    CLANG_VERSION=$1
else
    cd "${SCRIPT_DIR}"
    while true; do
        if [ -e defines.make ]; then
            CLANG_VERSION=$(make --no-print-directory --file=defines.make print-CLANG_VERSION)
            break
        elif [ $PWD == / ]; then
            failure "could not determine Clang version"
        else
            cd ..
        fi
    done
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

if [ ! ${CLANG_VERSION_PATTERNS[$CLANG_VERSION]+_} ]; then
    failure "This script does not support LLVM version $CLANG_VERSION"
fi

CLANG_VERSION_STRING=${CLANG_VERSION_PATTERNS[$CLANG_VERSION]}

# find the right repository name for the distro and version
case "$DIST_VERSION" in
    Debian_9*) REPO_NAME="deb http://apt.llvm.org/stretch/  llvm-toolchain-stretch$CLANG_VERSION_STRING main" ;;
    Debian_10*) REPO_NAME="deb http://apt.llvm.org/buster/   llvm-toolchain-buster$CLANG_VERSION_STRING  main" ;;
    Debian_unstable) REPO_NAME="deb http://apt.llvm.org/unstable/ llvm-toolchain$CLANG_VERSION_STRING         main" ;;
    Debian_testing) REPO_NAME="deb http://apt.llvm.org/unstable/ llvm-toolchain$CLANG_VERSION_STRING         main" ;;
    Ubuntu_16.04) REPO_NAME="deb http://apt.llvm.org/xenial/   llvm-toolchain-xenial$CLANG_VERSION_STRING  main" ;;
    Ubuntu_18.04) REPO_NAME="deb http://apt.llvm.org/bionic/   llvm-toolchain-bionic$CLANG_VERSION_STRING  main" ;;
    Ubuntu_18.10) REPO_NAME="deb http://apt.llvm.org/cosmic/   llvm-toolchain-cosmic$CLANG_VERSION_STRING  main" ;;
    Ubuntu_19.04) REPO_NAME="deb http://apt.llvm.org/disco/    llvm-toolchain-disco$CLANG_VERSION_STRING   main" ;;
    Ubuntu_19.10) REPO_NAME="deb http://apt.llvm.org/eoan/     llvm-toolchain-eoan$CLANG_VERSION_STRING    main" ;;
    Ubuntu_20.04) REPO_NAME="deb http://apt.llvm.org/focal/    llvm-toolchain-focal$CLANG_VERSION_STRING   main" ;;
    Ubuntu_20.10) REPO_NAME="deb http://apt.llvm.org/groovy/   llvm-toolchain-groovy$CLANG_VERSION_STRING  main" ;;
    Ubuntu_21.04) REPO_NAME="deb http://apt.llvm.org/hirsute/  llvm-toolchain-hirsute$CLANG_VERSION_STRING main" ;;
    Ubuntu_21.10) REPO_NAME="deb http://apt.llvm.org/impish/   llvm-toolchain-impish$CLANG_VERSION_STRING main" ;;
    Ubuntu_22.04) REPO_NAME="deb http://apt.llvm.org/jammy/   llvm-toolchain-jammy$CLANG_VERSION_STRING main" ;;
    *) failure "Distribution '$DISTRO' in version '$VERSION' is not supported by this script (${DIST_VERSION})." >&2 ;;
esac


# install everything
wget -O - https://apt.llvm.org/llvm-snapshot.gpg.key | apt-key add -
add-apt-repository "${REPO_NAME}"
apt-get update
apt-get install -y \
        clang-$CLANG_VERSION \
        clangd-$CLANG_VERSION \
        clang-format-$CLANG_VERSION \
        clang-tidy-$CLANG_VERSION \
        lld-$CLANG_VERSION \
        lldb-$CLANG_VERSION \
        libclang-$CLANG_VERSION-dev

"${SCRIPT_DIR}/install-iwyu.sh" --clang-version=$CLANG_VERSION
