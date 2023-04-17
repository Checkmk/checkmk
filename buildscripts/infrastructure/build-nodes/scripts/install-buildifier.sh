#!/bin/bash
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

set -e -o pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" >/dev/null 2>&1 && pwd)"
# shellcheck source=build_lib.sh
. "${SCRIPT_DIR}/build_lib.sh"

# We only ensure we use the right major version at the moment
GO_VERSION="1"
BUILDIFIER_VERSION="6.1.0"

install_package() {
    echo "Installing buildifier@${BUILDIFIER_VERSION}"
    # GO111MODULE=on is the default with Go 1.16
    GOPATH=/opt \
        GO111MODULE=on \
        go get github.com/bazelbuild/buildtools/buildifier@${BUILDIFIER_VERSION}
}

test_package() {
    log "Testing for go in \$PATH"
    go version | grep "go$GO_VERSION\." >/dev/null 2>&1 || (
        echo "Invalid version: $(go version)"
        exit 1
    )
}

case "$DISTRO" in
    ubuntu-20.04)
        install_package
        test_package
        ;;
    *)
        echo "ERROR: Unhandled DISTRO: $DISTRO - buildifier should only be available in IMAGE_TESTING!"
        exit 1
        ;;
esac
