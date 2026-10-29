#!/bin/bash
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

set -e -o pipefail

case "$DISTRO" in
    ubuntu-*)
        # installable on all Ubuntu versions to be potentially usable by developers
        echo "Installing for Ubuntu"

        apt-get update
        # Needed for building the agent deb/rpm packages.
        # Not needed for "make dist" itself.
        # Signing (dpkg-sig) happens in the package-signing image, see CMK-24094
        apt-get install -y \
            rpm \
            alien

        # Test the installations
        EXIT_STATUS=0
        rpm --version || EXIT_STATUS=$?
        alien --version || EXIT_STATUS=$?
        exit $EXIT_STATUS
        ;;
    *)
        echo "ERROR: Unhandled DISTRO: $DISTRO - rpm, alien should only be available for Ubuntu!"
        exit 1
        ;;
esac
