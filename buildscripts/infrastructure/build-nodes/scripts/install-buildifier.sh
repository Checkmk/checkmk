#!/bin/bash
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

set -e -o pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" >/dev/null 2>&1 && pwd)"
# shellcheck source=buildscripts/infrastructure/build-nodes/scripts/build_lib.sh
. "${SCRIPT_DIR}/build_lib.sh"

# We only ensure we use the right major version at the moment
GO_VERSION="1"
BUILDIFIER_VERSION="6.1.0"

install_package() {
    echo "Installing buildifier@${BUILDIFIER_VERSION}"
    # GO111MODULE=on is the default with Go 1.16
    GOPATH="${TARGET_DIR:-/opt}" \
        GO111MODULE=on \
        go install github.com/bazelbuild/buildtools/buildifier@${BUILDIFIER_VERSION}
}

case "$DISTRO" in
    ubuntu-*)
        install_package
        ;;
    *)
        echo "ERROR: Unhandled DISTRO: $DISTRO - buildifier currently only available in Ubuntu based reference images!"
        exit 1
        ;;
esac
test_package "go version" "go$GO_VERSION\."
