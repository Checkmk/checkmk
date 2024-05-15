#!/bin/bash
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

set -e -o pipefail

case "$DISTRO" in
    ubuntu-*)
        # installable on all Ubuntu versions to be potentially usable by developers
        echo "Installing for Ubuntu"

        # Install docker software
        curl -fsSL https://download.docker.com/linux/ubuntu/gpg | apt-key add -
        echo "deb [arch=amd64] https://download.docker.com/linux/ubuntu $(lsb_release -cs) stable" >/etc/apt/sources.list.d/docker.list
        apt-get update
        apt-get install -y docker-ce

        # Test the installation
        docker --version || exit $?
        ;;
    *)
        echo "ERROR: Unhandled DISTRO: $DISTRO - docker-ce should only be available in Ubuntu!"
        exit 1
        ;;
esac
