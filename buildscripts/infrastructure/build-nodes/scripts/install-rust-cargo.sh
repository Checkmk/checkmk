#!/bin/bash
# Copyright (C) 2021 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# This will install Rust + Cargo as described here:
# https://forge.rust-lang.org/infra/other-installation-methods.html#standalone-installers

set -e -o pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" >/dev/null 2>&1 && pwd)"

# provide common functions
. "${SCRIPT_DIR}/build_lib.sh"

RUST_VERSION="1.55.0"
DIR_NAME="rust-${RUST_VERSION}-x86_64-unknown-linux-gnu"
ARCHIVE_NAME="${DIR_NAME}.tar.gz"
TARGET_DIR=/opt

# Increase this to enforce a recreation of the build cache
BUILD_ID=2

build_package() {
    WORK_DIR=`mktemp -d`
    echo "TMP:" $WORK_DIR

    if [[ ! "$WORK_DIR" || ! -d "$WORK_DIR" ]]; then
      echo "Could not create temp dir"
      exit 1
    fi

    function cleanup {
      rm -rf "$WORK_DIR"
    }
    trap cleanup EXIT

    cd "$WORK_DIR"

    # Get the sources from nexus or upstream
    mirrored_download "${ARCHIVE_NAME}" "https://static.rust-lang.org/dist/${ARCHIVE_NAME}"

    tar xf "${ARCHIVE_NAME}"
    cd "${DIR_NAME}"
    ./install.sh --destdir="$TARGET_DIR" --prefix="${DIR_NAME}"
    rm -rf ${TARGET_DIR}/${DIR_NAME}/share/doc/rust
}

cached_build "${TARGET_DIR}" "${DIR_NAME}" "${BUILD_ID}" "${DISTRO}" "${BRANCH_VERSION}"
ln -sf "${TARGET_DIR}/${DIR_NAME}/bin/"* /usr/bin/

