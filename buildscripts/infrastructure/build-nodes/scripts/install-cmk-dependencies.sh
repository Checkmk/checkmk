#!/bin/bash
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# Prepares the current system (must be a supported distro) for installing a
# Checkmk package.

set -e -o pipefail

echo "Add Check_MK-pubkey.gpg to gpg"
gpg --import /opt/Check_MK-pubkey.gpg

case "$DISTRO" in
    centos-* | sles-*)
        echo "Add Check_MK-pubkey.gpg to RPM"
        rpm --import /opt/Check_MK-pubkey.gpg
        ;;
esac

# TODO: Install distro specific dependencies of Checkmk to make building of
# daily test container faster (since dependency installation is not needed
# anymore)
