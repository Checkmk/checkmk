#!/bin/bash
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# The test image is selected automatically, but can still be set via
# environment. e.g. for master:
# export IMAGE_ID="artifacts.lan.tribe29.com:4000/ubuntu-20.04:master-latest"

set -e

CHECKOUT_ROOT="$(git rev-parse --show-toplevel)"

# in case of worktrees $CHECKOUT_ROOT might not contain the actual repository clone
GIT_COMMON_DIR="$(realpath "$(git rev-parse --git-common-dir)")"

CMD="${*:-bash}"

# Make the registry login available within the container, e.g. for agent plugin unit tests which are pulling
# images from the registry within IMAGE_TESTING
DOCKER_CONF_PATH="${HOME}/.docker"
mkdir -p "${DOCKER_CONF_PATH}"

# This block makes sure a local containerized session does not interfere with
# native builds. Maybe in the future this script should not be executed in
# a CI environment (since those come with their own containerization solutions)
# rendering this distinction unnessesary.
if [ "$USER" == "jenkins" ]; then
    #
    # CI
    #
    # Needed for .cargo which is shared between workspaces
    SHARED_CARGO_FOLDER="${HOME}/shared_cargo_folder"
    LOCAL_CARGO_FOLDER="${CHECKOUT_ROOT}/shared_cargo_folder"
    mkdir -p "${SHARED_CARGO_FOLDER}" # in case it does not exist yet
    mkdir -p "${LOCAL_CARGO_FOLDER}"  # will be created with root-ownership instead
    CARGO_JENKINS_MOUNT="-v ${SHARED_CARGO_FOLDER}:${LOCAL_CARGO_FOLDER}"

    # We're using git reference clones, see also jenkins/global-defaults.yml in checkmk_ci.
    # That's why we need to mount the reference repos.
    GIT_REFERENCE_CLONE_PATH="/home/jenkins/git_reference_clones/check_mk.git"
    REFERENCE_CLONE_MOUNT="-v ${GIT_REFERENCE_CLONE_PATH}:${GIT_REFERENCE_CLONE_PATH}:ro"

    DOCKER_CONF_JENKINS_MOUNT="-v ${DOCKER_CONF_PATH}:${DOCKER_CONF_PATH}"
else
    #
    # LOCAL
    #
    # Create directories which otherwise would get created by root
    # rendering the native build broken
    mkdir -p "${CHECKOUT_ROOT}/.venv"
    mkdir -p "${CHECKOUT_ROOT}/omd/build"
    mkdir -p "${CHECKOUT_ROOT}/build_user_home/"

    if [ ! -d "${CHECKOUT_ROOT}/.docker_workspace/venv" ]; then
        CMD="touch ${CHECKOUT_ROOT}/Pipfile.lock; ${CMD[*]}"
    fi

    # Create directories for build artifacts which we want to have separated
    # in native and containerized builds
    # Here might be coming more, you keep an open eye, too, please

    mkdir -p "${CHECKOUT_ROOT}/.docker_workspace/venv"
    mkdir -p "${CHECKOUT_ROOT}/.docker_workspace/omd_build"
    mkdir -p "${CHECKOUT_ROOT}/.docker_workspace/home"
    DOCKER_LOCAL_ARGS="
        -v "${CHECKOUT_ROOT}/.docker_workspace/venv:${CHECKOUT_ROOT}/.venv" \
        -v "${CHECKOUT_ROOT}/.docker_workspace/omd_build:${CHECKOUT_ROOT}/omd/build" \
        -v "${CHECKOUT_ROOT}/.docker_workspace/home:${CHECKOUT_ROOT}/build_user_home/" \
        -e HOME="${CHECKOUT_ROOT}/build_user_home/" \
        "

    DOCKER_CONF_JENKINS_MOUNT="-v ${DOCKER_CONF_PATH}:${CHECKOUT_ROOT}/build_user_home/.docker"
fi

: "${IMAGE_ALIAS:=IMAGE_TESTING}"
"${CHECKOUT_ROOT}"/buildscripts/docker_image_aliases/resolve.py "${IMAGE_ALIAS}" --check
: "${IMAGE_ID:="$("${CHECKOUT_ROOT}"/buildscripts/docker_image_aliases/resolve.py "${IMAGE_ALIAS}")"}"
: "${TERMINAL_FLAG:="$([ -t 0 ] && echo ""--interactive --tty"" || echo "")"}"

if [ -t 0 ]; then
    echo "Running in Docker container from image ${IMAGE_ID} (cmd=${CMD}) (workdir=${PWD})"
fi

# shellcheck disable=SC2086
docker run -a stdout -a stderr \
    --rm \
    ${TERMINAL_FLAG} \
    --init \
    -u "$(id -u):$(id -g)" \
    -v "${CHECKOUT_ROOT}:${CHECKOUT_ROOT}" \
    -v "${GIT_COMMON_DIR}:${GIT_COMMON_DIR}" \
    ${CARGO_JENKINS_MOUNT} \
    ${DOCKER_LOCAL_ARGS} \
    ${REFERENCE_CLONE_MOUNT} \
    ${DOCKER_CONF_JENKINS_MOUNT} \
    -v "/var/run/docker.sock:/var/run/docker.sock" \
    --group-add="$(getent group docker | cut -d: -f3)" \
    -w "${PWD}" \
    -e BANDIT_OUTPUT_ARGS \
    -e GROOVYLINT_OUTPUT_ARGS \
    -e USER \
    -e JUNIT_XML \
    -e PYLINT_ARGS \
    -e PYTEST_ADDOPTS \
    -e DOCKER_ADDOPTS \
    -e MYPY_ADDOPTS \
    -e CI_TEST_SQL_DB_ENDPOINT \
    -e PYTHON_FILES \
    -e CHANGED_FILES \
    -e RESULTS \
    -e BAZEL_CACHE_URL \
    -e BAZEL_CACHE_USER \
    -e BAZEL_CACHE_PASSWORD \
    -e GERRIT_BRANCH \
    -e CI \
    -e GCC_TOOLCHAIN \
    -e DOCKER_REGISTRY_NO_HTTPS \
    ${DOCKER_RUN_ADDOPTS} \
    "${IMAGE_ID}" \
    sh -c "${CMD}"
