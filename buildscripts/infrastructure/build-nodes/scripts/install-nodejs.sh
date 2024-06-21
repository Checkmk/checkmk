#!/bin/bash
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

set -e -o pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" >/dev/null 2>&1 && pwd)"
# shellcheck source=buildscripts/infrastructure/build-nodes/scripts/build_lib.sh
. "${SCRIPT_DIR}/build_lib.sh"

# We only ensure we use the right major version at the moment
NODEJS_VERSION=$(get_version "$SCRIPT_DIR" NODEJS_VERSION)
NPM_VERSION=$(get_version "$SCRIPT_DIR" NPM_VERSION)

install_package() {
    # installable on all Ubuntu versions to be potentially usable by developers
    if [ "$(lsb_release -s -i)" != "Ubuntu" ]; then
        echo "ERROR: Unhandled DISTRO: $DISTRO"
        exit 1
    fi

    echo "Installing nodejs"
    mkdir -p /etc/apt/keyrings
    if [[ ! -e "/etc/apt/keyrings/nodesource.gpg" ]]; then
        curl -fsSL https://deb.nodesource.com/gpgkey/nodesource-repo.gpg.key | gpg --dearmor -o /etc/apt/keyrings/nodesource.gpg
    fi
    if [[ -e "/etc/apt/sources.list.d/nodesource.list" ]]; then
        if ! grep -Fxq "${NODEJS_VERSION}" /etc/apt/sources.list.d/nodesource.list; then
            echo "deb [signed-by=/etc/apt/keyrings/nodesource.gpg] https://deb.nodesource.com/node_$NODEJS_VERSION.x nodistro main" | tee /etc/apt/sources.list.d/nodesource.list
        fi
    else
        echo "deb [signed-by=/etc/apt/keyrings/nodesource.gpg] https://deb.nodesource.com/node_$NODEJS_VERSION.x nodistro main" | tee /etc/apt/sources.list.d/nodesource.list
    fi
    apt-get update
    apt-get install -y nodejs
}

install_package
test_package "node --version" "^v$NODEJS_VERSION\."
test_package "npm --version" "^$NPM_VERSION\."
