#!/bin/bash

set -e -o pipefail

# get the python version of the container if not specified
: "${PYTHON_VERSION_MAJ_MIN:="$(python -c 'import sys; print(".".join(map(str, sys.version_info[:2])));')"}"

install_packages() {
    echo "PYTHON_VERSION_MAJ_MIN: $PYTHON_VERSION_MAJ_MIN"

    # see Change-Id Ifae494bec4849ef7bd34348f8977310fb64b00e5
    if [ "$PYTHON_VERSION_MAJ_MIN" = "3.4" ]; then
        PYMONGO="pymongo==3.12"
    else
        PYMONGO="pymongo"
    fi
    echo "Specific PYMONGO package: $PYMONGO"

    # see Change-Id Ia88498098c77bf9199cf5ab9d8fb4d1e84133492
    python"${PYTHON_VERSION_MAJ_MIN}" -m pip install pytest pytest-mock mock requests "${PYMONGO}" --target "$(python"${PYTHON_VERSION_MAJ_MIN}" -c 'import sys; print(sys.path[-1])')"
}

populate_folders() {
    mkdir -p /tests /tests/datasets /agents
    cp -r tests/agent-plugin-unit/datasets/* /tests/datasets/
    cp -r agents/ /agents/
    find tests/agent-plugin-unit/ -maxdepth 1 -type f -exec cp {} /tests/ \;
}

run_test() {
    python"${PYTHON_VERSION_MAJ_MIN}" -m pytest "/tests"
}

while [[ $# -gt 0 ]]; do
    case "$1" in
        '-a' | '--all')
            install_packages
            populate_folders
            run_test
            shift
            ;;
        '-h' | '--help')
            echo "Choose from '--all' to run all steps, '--install' to install all Python packages, '--populate' to populate the required folders, '--help' to show this help"
            exit 0
            ;;
        '-i' | '--install')
            install_packages
            shift
            ;;
        '-p' | '--populate')
            populate_folders
            shift
            ;;
        '-r' | '--run')
            run_test
            shift
            ;;
        --* | -*)
            echo "Unknown option $1"
            exit 1
            ;;
    esac
done
