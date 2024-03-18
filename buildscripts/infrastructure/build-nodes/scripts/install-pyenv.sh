#!/bin/bash
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

set -e -o pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" >/dev/null 2>&1 && pwd)"
# SCRIPT_DIR="buildscripts/infrastructure/build-nodes/scripts"
# shellcheck source=buildscripts/infrastructure/build-nodes/scripts/build_lib.sh
. "${SCRIPT_DIR}/build_lib.sh"

TARGET_DIR="${TARGET_DIR:-/opt}"

install() {
    DESIRED_PYTHON_VERSION=$(get_desired_python_version "${SCRIPT_DIR}")
    print_debug "Desired python version: ${DESIRED_PYTHON_VERSION}"

    # source potential default pyenv path as the user calling this script did not source its bashrc file
    if [[ -d "$HOME/.pyenv/bin" ]]; then
        print_debug "Potential pyenv installation found"
        # there is a potential pyenv installation available
        export PYENV_ROOT="$HOME/.pyenv"
        export PATH="$PYENV_ROOT/bin:$PATH"
        eval "$(pyenv init -)"
    fi

    if type pyenv >/dev/null 2>&1; then
        # show me a better way to communicate between scripts called by different users
        echo "1" >>"${SCRIPT_DIR}"/INSTALLED_BY_PYENV

        # Update available versions for pyenv
        cd "$HOME"/.pyenv/plugins/python-build/../.. && git pull && cd -

        pyenv update
        pyenv install "${DESIRED_PYTHON_VERSION}" --skip-existing
        pyenv global "${DESIRED_PYTHON_VERSION}" # make pip3 available
        install_pipenv
    else
        print_blue "Team CI recommends to install pyenv for easy use. It is currently not yet installed."

        if [[ -n ${CI} ]]; then
            # CI build, don't ask
            INSTALL_PYENV="y"
        else
            read -rp "Should pyenv be installed now? (y/n): " INSTALL_PYENV
            echo # (optional) move to a new line
        fi
        if [[ $INSTALL_PYENV =~ ^[Yy]$ ]]; then
            # show me a better way to communicate between scripts called by different users
            echo "1" >>"${SCRIPT_DIR}"/INSTALLED_BY_PYENV
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
                # eval hack :P
                # a shebang with "#!/bin/bash -i" would work as well
                # https://askubuntu.com/questions/64387/cannot-successfully-source-bashrc-from-a-shell-script
                eval "$(tail -n -3 ~/.bashrc)"
            fi

            pyenv install "${DESIRED_PYTHON_VERSION}"
            pyenv global "${DESIRED_PYTHON_VERSION}" # make pip3 available
            install_pipenv
        fi
    fi
}

install_pipenv() {
    PIPENV_VERSION=$(get_version "$SCRIPT_DIR" PIPENV_VERSION)
    VIRTUALENV_VERSION=$(get_version "$SCRIPT_DIR" VIRTUALENV_VERSION)

    pip3 install \
        pipenv=="$PIPENV_VERSION" \
        virtualenv=="$VIRTUALENV_VERSION"

    # link pipenv to /usr/bin to be in PATH. Fallback to /opt/bin if no permissions for writting to /usr/bin.
    #   /opt/bin does not work as default, because `make -C omd deb` requires it to be in /usr/bin.
    #   only /usr/bin does not work, because GitHub Actions do not have permissions to write there.
    PIPENV_PATH=$(command -v pipenv)
    print_debug "Creating symlink to /usr/bin or ${TARGET_DIR}/bin for OMD usage"
    sudo ln -sf "${PIPENV_PATH}"* /usr/bin || sudo ln -sf "${PIPENV_PATH}"* "${TARGET_DIR}"/bin

    test_package "pipenv --version" "$PIPENV_VERSION$"
    test_package "pip3 freeze" "virtualenv"
}

install
