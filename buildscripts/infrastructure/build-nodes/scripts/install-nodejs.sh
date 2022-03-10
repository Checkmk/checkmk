#!/bin/bash
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

set -e -o pipefail

case "$DISTRO" in
centos-7 | centos-8)
    echo "Installing for CentOS 7, 8 (nodejs12)"
    curl -sL https://rpm.nodesource.com/setup_12.x | bash -
    yum -y install nodejs
    exit 0
    ;;
debian-* | ubuntu-* | cma*)
    echo "Installing for Debian / Ubuntu (nodejs12)"
    curl -sL https://deb.nodesource.com/setup_12.x | bash -
    apt-get install -y nodejs
    exit 0
    ;;
sles-15sp3)
    echo "Installing for SLES-15SP3 (nodejs14)"
    zypper -n --no-gpg-checks in --replacefiles --force-resolution nodejs14 npm14
    exit 0
    ;;
sles-15* | sles-12*)
    echo "Installing for SLES-* (nodejs10)"
    zypper -n --no-gpg-checks in --replacefiles --force-resolution nodejs10 npm10
    exit 0
    ;;
*)
    echo "ERROR: Unhandled DISTRO: $DISTRO"
    exit 1
    ;;
esac
