#!/bin/bash
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

set -e -o pipefail

case "$DISTRO" in
    ubuntu-*)
        echo "Installing for Ubuntu"

        # Install docker software
        apt-get update
        # Needed for building the agent deb/rpm packages
        apt-get install -y \
            rpm \
            alien
        # Needed for building the shipped OpenHardwareMonitorCLI.exe
        # TODO: We should really move this to a windows node based step
        apt-get install -y \
            mono-complete \
            mono-xbuild
        # Not needed for "make dist", but for the post-build steps of
        # buildscripts/scripts/build-cmk-version.jenkins
        apt-get install -y \
            dpkg-sig

        rm -rf /var/lib/apt/lists/*

        exit 0
        ;;
    *)
        echo "ERROR: Unhandled DISTRO: $DISTRO"
        exit 1
        ;;
esac
