#!/bin/bash
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

set -e -o pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" >/dev/null 2>&1 && pwd)"
# shellcheck source=build_lib.sh
. "${SCRIPT_DIR}/build_lib.sh"

# We only ensure we use the right major version at the moment
NODEJS_VERSION=$(get_version "$SCRIPT_DIR" NODEJS_VERSION)
NPM_VERSION=$(get_version "$SCRIPT_DIR" NPM_VERSION)

install_package() {
    if [ "$(lsb_release -s -i)" != "Ubuntu" ]; then
        echo "ERROR: Unhandled DISTRO: $DISTRO"
        exit 1
    fi

    echo "Installing nodejs"
    curl -sL "https://deb.nodesource.com/setup_$NODEJS_VERSION.x" | bash -
    apt-get install -y nodejs
}

test_package() {
    log "Testing for node v$NODEJS_VERSION in \$PATH"
    node --version | grep "^v$NODEJS_VERSION\." >/dev/null 2>&1 || (
        echo "Invalid version: $(node --version)"
        exit 1
    )

    log "Testing for npm $NPM_VERSION in \$PATH"
    npm --version | grep "^$NPM_VERSION\." >/dev/null 2>&1 || (
        echo "Invalid version: $(npm --version)"
        exit 1
    )
}

install_package
test_package
