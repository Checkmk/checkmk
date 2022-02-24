#!/bin/bash
# Copyright (C) 2021 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# This will install Rust + Cargo as described here:
# https://www.rust-lang.org/tools/install

set -e -o pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" >/dev/null 2>&1 && pwd)"

# provide common functions
. "${SCRIPT_DIR}/build_lib.sh"

DEFAULT_TOOLCHAIN="stable-x86_64-unknown-linux-gnu"
DIR_NAME="rust"
TARGET_DIR=/opt

CARGO_HOME="$TARGET_DIR/$DIR_NAME/cargo"
export CARGO_HOME
RUSTUP_HOME="$TARGET_DIR/$DIR_NAME/rustup"
export RUSTUP_HOME

# Increase this to enforce a recreation of the build cache
BUILD_ID=3

build_package() {
    WORK_DIR=$(mktemp -d)
    echo "TMP:" "$WORK_DIR"

    if [[ ! "$WORK_DIR" || ! -d "$WORK_DIR" ]]; then
      echo "Could not create temp dir"
      exit 1
    fi

    function cleanup {
      rm -rf "$WORK_DIR"
    }
    trap cleanup EXIT

    cd "$WORK_DIR"

    mirrored_download "rustup-init.sh" "https://sh.rustup.rs"
    chmod +x rustup-init.sh
    ./rustup-init.sh -y --no-modify-path --default-toolchain "$DEFAULT_TOOLCHAIN"
    ${CARGO_HOME}/bin/rustup target add x86_64-unknown-linux-musl
    # saves space
    rm -rf "$RUSTUP_HOME/toolchains/$DEFAULT_TOOLCHAIN/share/doc/"
}

cached_build "${TARGET_DIR}" "${DIR_NAME}" "${BUILD_ID}" "${DISTRO}" "${BRANCH_VERSION}"
ln -sf "${CARGO_HOME}/bin/"* /usr/bin/
