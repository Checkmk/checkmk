#!/bin/bash
# Copyright (C) 2021 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# This will install Rust + Cargo as described here:
# https://www.rust-lang.org/tools/install

set -e -o pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" >/dev/null 2>&1 && pwd)"
# shellcheck source=buildscripts/infrastructure/build-nodes/scripts/build_lib.sh
. "${SCRIPT_DIR}/build_lib.sh"

# define toolchain version explicitly
# 'stable' is allowed only for main(master) branch
TOOLCHAIN_VERSION="1.79"

DEFAULT_TOOLCHAIN="${TOOLCHAIN_VERSION}-x86_64-unknown-linux-gnu"
DIR_NAME="rust"
TARGET_DIR="${TARGET_DIR:-/opt}"

CARGO_HOME="$TARGET_DIR/$DIR_NAME/cargo"
export CARGO_HOME
RUSTUP_HOME="$TARGET_DIR/$DIR_NAME/rustup"
export RUSTUP_HOME

# Increase this to enforce a recreation of the build cache
BUILD_ID="8-$TOOLCHAIN_VERSION"

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
    "${CARGO_HOME}"/bin/rustup update
    "${CARGO_HOME}"/bin/rustup target add x86_64-unknown-linux-musl
    "${CARGO_HOME}"/bin/rustup default $TOOLCHAIN_VERSION

    # saves space
    rm -rf "$RUSTUP_HOME/toolchains/$DEFAULT_TOOLCHAIN/share/doc/"
    rm -rf "$RUSTUP_HOME/toolchains/$DEFAULT_TOOLCHAIN/share/man/"
    rm -rf "$RUSTUP_HOME/toolchains/$DEFAULT_TOOLCHAIN/share/zsh/"
}

if [ "$1" != "link-only" ]; then
    cached_build "${TARGET_DIR}" "${DIR_NAME}" "${BUILD_ID}" "${DISTRO}" "${BRANCH_VERSION}"
fi
ln -sf "${CARGO_HOME}/bin/"* /usr/bin/

test_package "rustc --version" "^rustc $TOOLCHAIN_VERSION\."
