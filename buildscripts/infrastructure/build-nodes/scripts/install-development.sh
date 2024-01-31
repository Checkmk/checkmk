#!/bin/bash
# Copyright (C) 2023 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# How to use
# ./buildscripts/infrastructure/build-nodes/scripts/install-development.sh \
#   --installpath $PWD/qwertz \
#   --profile cpp,python \
#   --dry
set -e -o pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" >/dev/null 2>&1 && pwd)"
# SCRIPT_DIR="buildscripts/infrastructure/build-nodes/scripts"
# shellcheck source=buildscripts/infrastructure/build-nodes/scripts/build_lib.sh
. "${SCRIPT_DIR}/build_lib.sh"

# some style settings defined here
resetColor=$'\e[0m'
txtRed=$'\e[41m'
txtGreen=$'\e[32m'
txtBlue=$'\e[34m'

IMPORTANT_MESSAGES=()

function print_red() {
    printf "%s%s%s\n" "${txtRed}" "$1" "${resetColor}"
}

function print_green() {
    printf "%s%s%s\n" "${txtGreen}" "$1" "${resetColor}"
}

function print_blue() {
    printf "%s%s%s\n" "${txtBlue}" "$1" "${resetColor}"
}

function print_debug() {
    print_blue "    $1"
}

function install_packages() {
    echo "Install for: ${*}"

    INSTALL_STR=""
    for i in "${@}"; do
        INSTALL_STR+="$i "
    done

    if [[ $DRY_RUN -gt 0 ]]; then
        print_blue "This is a dry run"
        print_blue "Would install these packages: '$INSTALL_STR'"
    else
        INSTALL_STR="apt-get install -y ${INSTALL_STR}"
        print_debug "$INSTALL_STR"
        apt-get update
        ${INSTALL_STR}
        rm -rf /var/lib/apt/lists/*
    fi
}

function install_basic_tools() {
    print_green "Installing common basic tools ..."
    local PACKAGES_TO_INSTALL=(
        "binutils"    # "strip" required to cleanup during strip_binaries
        "curl"        # curl is used to download artifacts from Nexus
        "gawk"        # TBC
        "git"         # git is used by install-[bazel, cmake, iwyu, patchelf, protobuf-cpp].sh
        "gnupg"       # "apt-key" used by install-docker
        "lsb-release" # lsb is used by install-[clang, docker, packer, nodejs].sh
        "make"        # don't forget your towel when you're taveling :)
        "sudo"        # some make calls require sudo
        "wget"        # wget is used by install-[clang, packer, protobuf-cpp].sh
    )
    install_packages "${PACKAGES_TO_INSTALL[@]}"
    print_green "Common basic tool installation done"
}

function copy_files_around() {
    print_green "Copy necessary files around and to ${INSTALL_PATH} ..."
    # /opt would be used in install-cmk-dependencies.sh by default
    mkdir -p "${INSTALL_PATH}"
    DISTRO_NAME=$(lsb_release -is)
    VERSION_NUMBER=$(lsb_release -sr)
    cp omd/distros/UBUNTU_"$VERSION_NUMBER".mk "${INSTALL_PATH}"
    # copy files to buildscripts/infrastructure/build-nodes/scripts
    cp .bazelversion defines.make package_versions.bzl static_variables.bzl "${SCRIPT_DIR}"
    print_green "Necessary file copying done"
}

function perform_cleanup() {
    print_green "Cleanup ..."
    rm "${INSTALL_PATH}"/UBUNTU_"$VERSION_NUMBER".mk
    rm "${SCRIPT_DIR}"/.bazelversion
    rm "${SCRIPT_DIR}"/defines.make
    rm "${SCRIPT_DIR}"/static_variables.bzl
    rm "${SCRIPT_DIR}"/package_versions.bzl
    rm -f "${SCRIPT_DIR}"/*.mk
    print_green "Cleanup done"
}

function setup_env_variables() {
    print_green "Setup env variables ..."
    DISTRO_NAME=$(lsb_release -is)
    VERSION_NUMBER=$(lsb_release -sr)
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
    export DISTRO_NAME
    export VERSION_NUMBER
    print_debug "DISTRO                = ${DISTRO}"
    print_debug "DISTRO_NAME           = ${DISTRO_NAME}"
    print_debug "VERSION_NUMBER        = ${VERSION_NUMBER}"
    print_debug "NEXUS_ARCHIVES_URL    = ${NEXUS_ARCHIVES_URL}"
    print_debug "BRANCH_NAME           = ${BRANCH_NAME}"
    print_debug "BRANCH_VERSION        = ${BRANCH_VERSION}"
    print_debug "CLANG_VERSION         = ${CLANG_VERSION}"
    print_debug "PIPENV_VERSION        = ${PIPENV_VERSION}"
    print_debug "VIRTUALENV_VERSION    = ${VIRTUALENV_VERSION}"
    print_green "Env variables setup done"
}

function collect_user_input() {
    print_green "Collect user input ..."
    print_debug "... to get artifacts instead of building from scratch"
    read -rp "Enter Nexus Username: " NEXUS_USERNAME
    export NEXUS_USERNAME
    read -rsp "Enter Nexus Password: " NEXUS_PASSWORD
    export NEXUS_PASSWORD
    echo
    print_green "User input collection done"
}

function strip_binaries() {
    if [[ -n ${CI} ]]; then
        # CI build, located at /opt
        /opt/strip_binaries "${INSTALL_PATH}"
    else
        omd/strip_binaries "${INSTALL_PATH}"
    fi
}

function get_desired_python_version() {
    # to use "make print-PYTHON_VERISON" the git repo with "Makefile" and "artifacts.make" would be necessary at a known location
    sed -n 's|^PYTHON_VERSION = \"\(\S*\)\"$|\1|p' "${SCRIPT_DIR}"/package_versions.bzl
}

function install_for_python_dev() {
    print_green "Installing everything for Python development ..."

    local PACKAGES_TO_INSTALL=(
        # https://github.com/pyenv/pyenv/wiki#suggested-build-environment
        "build-essential"
        "libssl-dev"
        "zlib1g-dev"
        "libbz2-dev"
        "libreadline-dev"
        "libsqlite3-dev"
        "libncursesw5-dev"
        "xz-utils"
        "tk-dev"
        "libxml2-dev"
        "libxmlsec1-dev"
        "libffi-dev"
        "liblzma-dev"
    )
    install_packages "${PACKAGES_TO_INSTALL[@]}"

    if type pyenv >/dev/null 2>&1; then
        pyenv install "$(get_desired_python_version)"
        pyenv global "$(get_desired_python_version)" # make pip3 available
    else
        print_blue "Team CI recommends to install pyenv for easy use. It is currently not yet installed."

        if [[ -n ${CI} ]]; then
            # CI build, don't ask
            INSTALL_PYENV="y"
        else
            read -rp "Should pyenv it be installed now? (y/n): " INSTALL_PYENV
            echo # (optional) move to a new line
        fi
        if [[ $INSTALL_PYENV =~ ^[Yy]$ ]]; then
            INSTALLED_BY_PYENV=1
            curl https://pyenv.run | bash

            cat <<'EOF' >>~/.bashrc
export PYENV_ROOT="$HOME/.pyenv"
command -v pyenv >/dev/null || export PATH="$PYENV_ROOT/bin:$PATH"
eval "$(pyenv init -)"
EOF

            if [[ -n ${CI} ]]; then
                # CI build
                export PYENV_ROOT="$HOME/.pyenv"
                export PATH="$PYENV_ROOT/bin:$PATH"
                eval "$(pyenv init -)"
            else
                # source the extended bashrc file to ensure everything went well
                # SC1090: Can't follow non-constant source. Use a directive to specify location.
                # shellcheck disable=SC1090
                source ~/.bashrc
            fi

            pyenv install "$(get_desired_python_version)"
            pyenv global "$(get_desired_python_version)" # make pip3 available
        else
            print_blue "All right, Python will be installed as done in the CI to $TARGET_DIR"
            install_python_and_teammates
        fi
    fi

    "${SCRIPT_DIR}"/install-pipenv.sh

    print_green "Installation for Python development done"
}

function install_python_and_teammates() {
    export TARGET_DIR="${INSTALL_PATH}"
    "${SCRIPT_DIR}"/install-openssl.sh
    "${SCRIPT_DIR}"/install-python.sh

    if [[ $STRIP_LATER -eq 1 ]]; then
        print_blue "strip_binaries during Python setup"
        strip_binaries
        "${SCRIPT_DIR}"/install-python.sh link-only
    fi
}

function install_for_cpp_dev() {
    print_green "Installing everything for CPP development ..."

    local PACKAGES_TO_INSTALL=(
        "python3-dev"     # "libpython3.10.so.1.0" required by gdb, ouch
        "pkg-config"      # used by install-protobuf-cpp.sh
        "build-essential" # why not
        # the following packages are copied from the old make setup step
        "direnv"
        "doxygen"
        "ksh"
        "libjpeg-dev"
        "libkrb5-dev"
        "libldap2-dev"
        "libmariadb-dev-compat"
        "libpcap-dev"
        "libpango1.0-dev"
        "libpq-dev"
        "libreadline-dev"
        "librrd-dev"
        "libsasl2-dev"
        "libsqlite3-dev"
        "libtool-bin"
        "libxml2-dev"
        "libxslt-dev"
        "p7zip-full"
        "zlib1g-dev"
    )
    install_packages "${PACKAGES_TO_INSTALL[@]}"

    export TARGET_DIR="${INSTALL_PATH}"
    # /usr/bin/gdb: error while loading shared libraries: libpython3.11.so.1.0:
    # cannot open shared object file: No such file or directory
    "${SCRIPT_DIR}"/install-gnu-toolchain.sh
    "${SCRIPT_DIR}"/install-valgrind.sh
    "${SCRIPT_DIR}"/install-cmake.sh
    "${SCRIPT_DIR}"/install-clang.sh
    "${SCRIPT_DIR}"/install-protobuf-cpp.sh
    "${SCRIPT_DIR}"/install-freetds.sh

    if [[ $STRIP_LATER -eq 1 ]]; then
        print_blue "strip_binaries during CPP setup"
        strip_binaries

        "${SCRIPT_DIR}"/install-gnu-toolchain.sh link-only
        "${SCRIPT_DIR}"/install-valgrind.sh link-only
        "${SCRIPT_DIR}"/install-cmake.sh link-only
        # no need to link aka install protobuf again
        # "${SCRIPT_DIR}"/install-protobuf-cpp.sh --link-only
        "${SCRIPT_DIR}"/install-freetds.sh link-only
    fi

    "${SCRIPT_DIR}"/install-patchelf.sh

    print_green "Installation for CPP development done"
}

function install_cmk_package_dependencies() {
    print_green "Installing everything for CMK development ..."

    "${SCRIPT_DIR}"/install-cmk-dependencies.sh

    print_green "Installation for CMK development done"
}

function install_for_rust_dev() {
    print_green "Installing everything for Rust development ..."

    export TARGET_DIR="${INSTALL_PATH}"
    "${SCRIPT_DIR}"/install-freetds.sh
    "${SCRIPT_DIR}"/install-rust-cargo.sh

    if [[ $STRIP_LATER -eq 1 ]]; then
        print_blue "strip_binaries during Rust setup"
        strip_binaries
        "${SCRIPT_DIR}"/install-rust-cargo.sh link-only
    fi

    print_green "Installation for Rust development done"

    IMPORTANT_MESSAGES+=("Don't forget to call: export RUSTUP_HOME=${INSTALL_PATH}/rust/rustup")
    print_red "${IMPORTANT_MESSAGES[${#IMPORTANT_MESSAGES[@]} - 1]}"
}

function install_for_frontend_dev() {
    print_green "Installing everything for Frontend development ..."

    "${SCRIPT_DIR}"/install-nodejs.sh

    print_green "Installation for Frontend development done"
}

function install_for_localize_dev() {
    print_green "Installing everything for Localization development ..."

    install_packages gettext

    print_green "Installation for Localization development done"
}

POSITIONAL_ARGS=()
PROFILE_ARGS=()
INSTALL_PATH=/opt
while [[ $# -gt 0 ]]; do
    case $1 in
        --dry)
            DRY_RUN=1
            shift # past argument
            ;;
        -p | --installpath)
            INSTALL_PATH="$2"
            shift # past argument
            shift # past value
            print_red "Installation might take longer, some tools need to be built from scratch"
            print_red "Custom installation path is not yet supported"
            exit 1
            ;;
        --profile)
            INSTALL_PROFILE="$2"
            IFS=',' read -ra PROFILE_ARGS <<<"$INSTALL_PROFILE"
            shift # past argument
            shift # past value
            ;;
        --* | -*)
            echo "Unknown option $1"
            exit 1
            ;;
        *)
            POSITIONAL_ARGS+=("$1") # save positional arg
            shift                   # past argument
            ;;
    esac
done
set -- "${POSITIONAL_ARGS[@]}" # restore positional parameters

print_debug "SCRIPT_DIR      = ${SCRIPT_DIR}"
print_debug "INSTALL_PATH    = ${INSTALL_PATH}"
print_debug "INSTALL_PROFILE = ${INSTALL_PROFILE}"
print_debug "DRY_RUN         = ${DRY_RUN}"
print_debug "POSITIONAL_ARGS = ${POSITIONAL_ARGS[*]}"
print_debug "PROFILE_ARGS    = ${PROFILE_ARGS[*]}"

REQUIRES_NEXUS=0
INSTALL_FOR_PYTHON=0
INSTALL_FOR_CPP=0
INSTALL_FOR_RUST=0
INSTALL_FOR_FRONTEND=0
INSTALL_FOR_LOCALIZE=0
INSTALLED_BY_PYENV=0
# strip only once, if "all" or multiple profiles selected, do it at the end
STRIP_LATER=0
for PROFILE in "${PROFILE_ARGS[@]}"; do
    case "$PROFILE" in
        all)
            ((REQUIRES_NEXUS += 1))
            INSTALL_FOR_PYTHON=1
            INSTALL_FOR_CPP=1
            INSTALL_FOR_RUST=1
            INSTALL_FOR_FRONTEND=1
            INSTALL_FOR_LOCALIZE=1
            ((STRIP_LATER += 5))
            ;;
        python)
            ((REQUIRES_NEXUS += 1))
            INSTALL_FOR_PYTHON=1
            ((STRIP_LATER += 1))
            ;;
        cpp)
            ((REQUIRES_NEXUS += 1))
            INSTALL_FOR_CPP=1
            ((STRIP_LATER += 1))
            ;;
        rust)
            ((REQUIRES_NEXUS += 1))
            INSTALL_FOR_RUST=1
            ((STRIP_LATER += 1))
            ;;
        frontend)
            INSTALL_FOR_FRONTEND=1
            ;;
        localize)
            INSTALL_FOR_LOCALIZE=1
            ;;
        *)
            print_red "Unknown installation profile $INSTALL_PROFILE"
            print_debug "Choose from 'all', 'python', 'cpp', 'rust', 'frontend', 'localize'"
            exit 1
            ;;
    esac
done
print_debug "INSTALL_FOR_PYTHON   = ${INSTALL_FOR_PYTHON}"
print_debug "INSTALL_FOR_CPP      = ${INSTALL_FOR_CPP}"
print_debug "INSTALL_FOR_RUST     = ${INSTALL_FOR_RUST}"
print_debug "INSTALL_FOR_FRONTEND = ${INSTALL_FOR_FRONTEND}"
print_debug "INSTALL_FOR_LOCALIZE = ${INSTALL_FOR_LOCALIZE}"
print_debug "REQUIRES_NEXUS       = ${REQUIRES_NEXUS}"
print_debug "STRIP_LATER          = ${STRIP_LATER}"

if [[ -n ${CI} ]]; then
    print_debug "It is a CI build, don't ask for a password"
    REQUIRES_NEXUS=0
else
    print_debug "No CI build, ask human for password if required"
fi

if [[ $REQUIRES_NEXUS -ge 1 ]]; then
    collect_user_input
fi

install_basic_tools
if [[ -z ${CI} ]]; then
    # non CI build, Dockerfile is responsible for placing the files
    copy_files_around
fi
setup_env_variables

# basic tools and env variables required to install docker
"${SCRIPT_DIR}"/install-docker.sh

# CPP, actually "python3-dev" needs to be installed/called before install-python.sh
# to have "libpython3.10.so.1.0" available for gdb
if [[ $INSTALL_FOR_CPP -eq 1 ]]; then
    install_for_cpp_dev
fi
if [[ $INSTALL_FOR_PYTHON -eq 1 ]]; then
    install_for_python_dev
fi
if [[ $INSTALL_FOR_RUST -eq 1 ]]; then
    install_for_rust_dev
fi
if [[ $INSTALL_FOR_FRONTEND -eq 1 ]]; then
    install_for_frontend_dev
fi
if [[ $INSTALL_FOR_LOCALIZE -eq 1 ]]; then
    install_for_localize_dev
fi

if [[ $STRIP_LATER -gt 1 ]]; then
    print_blue "strip_binaries finally"
    strip_binaries

    if [[ $INSTALL_FOR_CPP -eq 1 ]]; then
        print_debug "Link CPP things"
        "${SCRIPT_DIR}"/install-gnu-toolchain.sh link-only
        "${SCRIPT_DIR}"/install-valgrind.sh link-only
        "${SCRIPT_DIR}"/install-cmake.sh link-only
        # no need to link aka install protobuf again
        # "${SCRIPT_DIR}"/install-protobuf-cpp.sh link-only
        "${SCRIPT_DIR}"/install-freetds.sh link-only
    fi

    if [[ $INSTALL_FOR_PYTHON -eq 1 && $INSTALLED_BY_PYENV -eq 0 ]]; then
        print_debug "Link Python"
        "${SCRIPT_DIR}"/install-python.sh link-only
    fi

    if [[ $INSTALL_FOR_RUST -eq 1 ]]; then
        print_debug "Link Rust"
        "${SCRIPT_DIR}"/install-rust-cargo.sh link-only
    fi
fi

# CMK dependencies should always be installed
install_cmk_package_dependencies

if [[ $REQUIRES_NEXUS -gt 0 ]]; then
    # only localize or web is installed, which don't require nexus interactions
    # install Bazel for package building
    export TARGET_DIR="${INSTALL_PATH}"
    "${SCRIPT_DIR}"/install-bazel.sh
fi

# install_packages golang-go
# "${SCRIPT_DIR}"/install-buildifier.sh

perform_cleanup

if [[ ${#IMPORTANT_MESSAGES[@]} -gt 0 ]]; then
    for i in "${IMPORTANT_MESSAGES[@]}"; do
        print_red "$i"
    done
fi

exit 0
