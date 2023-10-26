#!/bin/bash
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

set -e -o pipefail

SCRIPT_DIR="buildscripts/infrastructure/build-nodes/scripts"
# shellcheck source=buildscripts/infrastructure/build-nodes/scripts/build_lib.sh
. "${SCRIPT_DIR}/build_lib.sh"

echo "Installing necessary basic tools ..."
apt-get update
apt-get install \
    git \
    lsb-release \
    wget
echo "Done"

echo "Performing setup (copy files around) ..."
mkdir -p /opt
DISTRO_NAME=$(lsb_release -is)
VERSION_NUMBER=$(lsb_release -sr)
# /opt is used by install-cmk-dependencies.sh, sorry about that
cp omd/distros/UBUNTU_"$VERSION_NUMBER".mk /opt
cp defines.make static_variables.bzl buildscripts/infrastructure/build-nodes/scripts
echo "Done"

echo "Setup env variables ..."
BRANCH_NAME=$(get_version "$SCRIPT_DIR" BRANCH_NAME)
BRANCH_VERSION=$(get_version "$SCRIPT_DIR" BRANCH_VERSION)
CLANG_VERSION=$(get_version "$SCRIPT_DIR" CLANG_VERSION)
PIPENV_VERSION=$(get_version "$SCRIPT_DIR" PIPENV_VERSION)
VIRTUALENV_VERSION=$(get_version "$SCRIPT_DIR" VIRTUALENV_VERSION)
export DISTRO="${DISTRO_NAME,,}-${VERSION_NUMBER}"
export NEXUS_ARCHIVES_URL="https://artifacts.lan.tribe29.com/repository/archives/"
export BRANCH_NAME
export BRANCH_VERSION
export CLANG_VERSION
export PIPENV_VERSION
export VIRTUALENV_VERSION
echo "Done"

echo "Collect user input ..."
read -rp "Enter Nexus Username: " NEXUS_USERNAME
export NEXUS_USERNAME
read -rsp "Enter Nexus Password: " NEXUS_PASSWORD
export NEXUS_PASSWORD
echo "Done"

echo "Installing additional tools ..."
# librrd-dev is still needed by the python rrd package we build in our virtual environment
apt-get install \
    autoconf \
    build-essential \
    python3-pip \
    software-properties-common \
    clang-tools \
    direnv \
    doxygen \
    figlet \
    gawk \
    ksh \
    libjpeg-dev \
    libkrb5-dev \
    libldap2-dev \
    libmariadb-dev-compat \
    libpango1.0-dev \
    libpcap-dev \
    librrd-dev \
    libsasl2-dev \
    libsqlite3-dev \
    libtool-bin \
    libxml2-dev \
    libreadline-dev \
    libxslt-dev \
    libpq-dev \
    libreadline-dev \
    p7zip-full \
    pngcrush \
    python3-pip \
    python3-venv \
    zlib1g-dev
echo "Done"

echo "Installing CMK dependencies ..."
buildscripts/infrastructure/build-nodes/scripts/install-cmk-dependencies.sh
echo "Done"

echo "Installing cmake ..."
buildscripts/infrastructure/build-nodes/scripts/install-cmake.sh
echo "Done"

echo "Installing clang ..."
buildscripts/infrastructure/build-nodes/scripts/install-clang.sh
echo "Done"

echo "Installing docker ..."
buildscripts/infrastructure/build-nodes/scripts/install-docker.sh
# do not add the sudo user to the docker group, see "linux-advanced-users" slack channel announcement
echo "Done"

echo "Installing musl-tools ..."
buildscripts/infrastructure/build-nodes/scripts/install-musl-tools.sh
echo "Done"

echo "Installing patchelf ..."
buildscripts/infrastructure/build-nodes/scripts/install-patchelf.sh
echo "Done"

echo "Installing shellcheck ..."
buildscripts/infrastructure/build-nodes/scripts/install-shellcheck.sh
echo "Done"

echo "Installing valgrind ..."
buildscripts/infrastructure/build-nodes/scripts/install-valgrind.sh
echo "Done"

echo "Installing and setting up PyEnv and pip ..."
python3 -m pip install --user --upgrade pipenv
if type pyenv >/dev/null 2>&1 && pyenv shims --short | grep '^pipenv$'; then
    CMD="pyenv exec"
else
    CMD=""
fi
$CMD pip3 install --user --upgrade \
    pip \
    pipenv=="${PIPENV_VERSION}" \
    virtualenv=="${VIRTUALENV_VERSION}" \
    wheel
echo "Done"

echo "Installing rustup ..."
buildscripts/infrastructure/build-nodes/scripts/install-rust-cargo.sh
echo "Done"

make -C web setup

make -C locale setup
make check-setup

echo "Cleanup ..."
rm /opt/UBUNTU_"$VERSION_NUMBER".mk
rm buildscripts/infrastructure/build-nodes/scripts/defines.make
rm buildscripts/infrastructure/build-nodes/scripts/static_variables.bzl
echo "Done"
