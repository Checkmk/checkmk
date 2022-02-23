#!/bin/bash
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

set -e -o pipefail

case "$DISTRO" in
    ubuntu-*)
        echo "Installing for Ubuntu"

        apt-get update
        apt-get install -y shellcheck
        rm -rf /var/lib/apt/lists/*

        exit 0
        ;;
    *)
        echo "ERROR: Unhandled DISTRO: $DISTRO"
        exit 1
        ;;
esac
