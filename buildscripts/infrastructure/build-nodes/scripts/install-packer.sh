#!/bin/bash
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

set -e -o pipefail

case "$DISTRO" in
    ubuntu-*)
        # installable on all Ubuntu versions to be potentially usable by developers
        echo "Installing for Ubuntu"
        wget -O- https://apt.releases.hashicorp.com/gpg |
            gpg --dearmor |
            sudo tee /usr/share/keyrings/hashicorp-archive-keyring.gpg >/dev/null
        echo "deb [signed-by=/usr/share/keyrings/hashicorp-archive-keyring.gpg] https://apt.releases.hashicorp.com $(lsb_release -cs) main" | sudo tee /etc/apt/sources.list.d/hashicorp.list
        apt-get update
        apt-get install -y packer

        # Test the installation
        packer --version || exit $?
        ;;
    *)
        echo "ERROR: Unhandled DISTRO: $DISTRO - packer should only be available in Ubuntu!"
        exit 1
        ;;
esac
