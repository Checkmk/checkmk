#!/bin/bash
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

set -e -o pipefail

case "$DISTRO" in
    ubuntu-20.04)
        echo "Installing for Ubuntu"

        curl -s "https://awscli.amazonaws.com/awscli-exe-linux-x86_64-2.11.9.zip" -o "awscliv2.zip"
        unzip -q awscliv2.zip
        ./aws/install
        rm -r aws awscliv2.zip

        # Test the installation
        aws --version || exit $?
        ;;
    *)
        echo "ERROR: Unhandled DISTRO: $DISTRO - aws-cli should only be available in IMAGE_TESTING!"
        exit 1
        ;;
esac
