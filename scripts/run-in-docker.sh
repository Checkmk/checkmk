#!/bin/bash
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# The test image is selected automatically, but can still be set via
# enviroment. e.g. for master:
# export IMAGE_ID="artifacts.lan.tribe29.com:4000/ubuntu-20.04:master-latest"

set -e

REPO_DIR="$(git rev-parse --show-toplevel)"

# in case of worktrees $REPO_DIR might not contain the actual repository clone
GIT_COMMON_DIR="$(realpath "$(git rev-parse --git-common-dir)")"

CMD="$*"

# This block makes sure a local containerized session does not interfere with
# native builds. Maybe in the future this script should not be executed in
# a CI environment (since those come with their own containerization solutions)
# rendering this distinction unnessesary.
if [ "$USER" != "jenkins" ]; then
    # Create directories which otherwise would get created by root
    # rendering the native build broken
    mkdir -p "${REPO_DIR}/.venv"
    mkdir -p "${REPO_DIR}/omd/build"
    mkdir -p "${REPO_DIR}/build_user_home/"

    if [ ! -d "${REPO_DIR}/.docker_workspace/venv" ]; then
        CMD="touch ${REPO_DIR}/Pipfile.lock; $*"
    fi

    # Create directories for build artifacts which we want to have separated
    # in native and containerized builds
    # Here might be coming more, you keep an open eye, too, please

    mkdir -p "${REPO_DIR}/.docker_workspace/venv"
    mkdir -p "${REPO_DIR}/.docker_workspace/omd_build"
    mkdir -p "${REPO_DIR}/.docker_workspace/home"
    DOCKER_LOCAL_ARGS="
        -v "${REPO_DIR}/.docker_workspace/venv:${REPO_DIR}/.venv" \
        -v "${REPO_DIR}/.docker_workspace/omd_build:${REPO_DIR}/omd/build" \
        -v "${REPO_DIR}/.docker_workspace/home:${REPO_DIR}/build_user_home/" \
        -e HOME="${REPO_DIR}/build_user_home/" \
        "
fi

: "${IMAGE_ALIAS:=IMAGE_TESTING}"
: "${IMAGE_ID:="$("${REPO_DIR}"/buildscripts/docker_image_aliases/resolve.sh "${IMAGE_ALIAS}")"}"

echo "Running in Docker container from image ${IMAGE_ID} (cmd=$*) (workdir=${PWD})"

# shellcheck disable=SC2086
docker run -t -a stdout -a stderr \
    --rm \
    --init \
    -u "${UID}:$(id -g)" \
    -v "${REPO_DIR}:${REPO_DIR}" \
    -v "${GIT_COMMON_DIR}:${GIT_COMMON_DIR}" \
    ${DOCKER_LOCAL_ARGS} \
    -v "/var/run/docker.sock:/var/run/docker.sock" \
    --group-add="$(getent group docker | cut -d: -f3)" \
    -w "${PWD}" \
    -e JUNIT_XML \
    -e PYLINT_ARGS \
    -e PYTEST_ADDOPTS \
    -e DOCKER_ADDOPTS \
    -e MYPY_ADDOPTS \
    -e PYTHON_FILES \
    -e RESULTS \
    -e WORKDIR \
    -e CI \
    ${DOCKER_RUN_ADDOPTS} \
    "${IMAGE_ID}" \
    sh -c "${CMD}"
