#!/bin/bash

set -e -o pipefail

SOURCES_LIST="$(dirname "$0")/sources-list.txt"
STAGE_DIR="/stage"

install_packages() {
    echo "PYTHON_VERSION_MAJ_MIN: ${PYTHON_VERSION_MAJ_MIN?}"

    # see Change-Id Ifae494bec4849ef7bd34348f8977310fb64b00e5
    if [ "${PYTHON_VERSION_MAJ_MIN?}" = "3.4" ]; then
        PYMONGO="pymongo==3.12"
    else
        PYMONGO="pymongo"
    fi
    echo "Specific PYMONGO package: $PYMONGO"

    # see Change-Id Ia88498098c77bf9199cf5ab9d8fb4d1e84133492
    python"${PYTHON_VERSION_MAJ_MIN?}" -m pip install pytest pytest-mock mock requests "${PYMONGO}" --target "$(python"${PYTHON_VERSION_MAJ_MIN?}" -c 'import sys; print(sys.path[-1])')"
}

query_rel_sources() {
    ws="$(bazel info | grep "workspace:" | cut -d' ' -f2)"
    bazel query 'kind("source file", deps(attr(tags, "legacy-python", //...)))' --output=location |
        grep -v @ |
        grep -v pyproject.toml |
        cut -d: -f1 |
        sed "s|${ws}/||"
}

replay_rel_sources() {
    # I would love to use query_rel_sources directly here,
    # but this stage runs in a context that doesn't have
    # bazel :-(. Adding it would be very expensive.
    # So instead, we store the result of the query in a
    # file, and only ensure it is up to date.
    grep -v '^#' "${SOURCES_LIST}"
}

check_sources() {
    expected="$(query_rel_sources | sort)"
    actual="$(replay_rel_sources | sort)"

    new=$(comm -13 <(echo "${actual}") <(echo "${expected}"))
    remove=$(comm -23 <(echo "${actual}") <(echo "${expected}"))

    if [ -n "${new}" ]; then
        echo "Files missing from ${SOURCES_LIST}:"
        echo "${new}"
    fi

    if [ -n "${remove}" ]; then
        echo "Files to remove from ${SOURCES_LIST}:"
        echo "${remove}"
    fi

    [ -z "${new}${remove}" ]
}

populate_folders() {
    echo "Populating ${STAGE_DIR?} ..."
    replay_rel_sources | while read -r src; do
        mkdir -p "${STAGE_DIR?}/$(dirname "${src}")"
        cp "${src}" "${STAGE_DIR?}/${src}"
    done

    # mk_podman requires Python 3.8+ (walrus operator, dataclasses, etc.)
    podman_test="${STAGE_DIR?}/tests/agent-plugin-unit/test_mk_podman.py"
    case "${PYTHON_VERSION_MAJ_MIN?}" in
        3.4 | 3.5 | 3.6 | 3.7) rm "${podman_test}" ;;
    esac
}

run_test() {
    (
        cd "${STAGE_DIR?}"
        python"${PYTHON_VERSION_MAJ_MIN?}" -m pytest .
    )
}

case "$1" in
    '--check-sources')
        check_sources
        ;;
    '--execute')
        populate_folders
        install_packages
        run_test
        ;;
    *)
        echo "Unknown option $1"
        exit 1
        ;;
esac
