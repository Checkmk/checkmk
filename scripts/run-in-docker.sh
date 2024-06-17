#!/bin/bash
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# Runs attached command in a Docker container.
# By default the 'reference image' will be used to create the container, but this
# behavior can be customized using either @IMAGE_ALIAS or @IMAGE_ID as follows:
#   run-in-docker.sh <CMD>                                     will use reference image
#   IMAGE_ALIAS=IMAGE_CENTOS_8 run-in-docker.sh <CMD>          will use dereferenced image alias IMAGE_CENTOS_8
#   IMAGE_ID=ubuntu-20.04:2.3.0-latest run-in-docker.sh <CMD>  will use provided image id directly
# Also DOCKER_RUN_ADDOPTS can be set to add additional arguments to be passed to `docker run`
#
# To re-build the container from scratch:
#   docker buildx prune --all
#   docker rmi $(docker images -f "dangling=true" -q)
#   rm -r container_shadow_workspace_local/venv/
#   ./scripts/run-in-docker.sh <CMD>
#
# Get more details about the reference image and other things with:
#   VERBOSE=1 ./scripts/run-in-docker.sh <CMD>

set -e

CHECKOUT_ROOT="$(git rev-parse --show-toplevel)"

# in case of worktrees $CHECKOUT_ROOT might not contain the actual repository clone
GIT_COMMON_DIR="$(realpath "$(git rev-parse --git-common-dir)")"

CMD="${*:-bash}"

# Create directories for build artifacts which we want to have separated
# in native and containerized builds
# Here might be coming more, you keep an open eye, too, please
# Create directories which otherwise would get created by root
# rendering the native build broken

if [ "$USER" == "jenkins" ]; then
    # CI
    CONTAINER_SHADOW_WORKSPACE="$(dirname "${CHECKOUT_ROOT}")/container_shadow_workspace_ci"
    echo >&2 "WARNING: run-in-docker.sh used in CI. This should not happen. Use CI native tools instead"
else
    # LOCAL
    CONTAINER_SHADOW_WORKSPACE="${CHECKOUT_ROOT}/container_shadow_workspace_local"

    # Make sure a local containerized session does not interfere with
    # native builds. Maybe in the future this script should not be executed in
    # a CI environment (since those come with their own containerization solutions)
    # rendering this distinction unnessesary.

    mkdir -p "${CHECKOUT_ROOT}/.venv"
    mkdir -p "${CONTAINER_SHADOW_WORKSPACE}/venv"
    DOCKER_MOUNT_ARGS="${DOCKER_MOUNT_ARGS} -v ${CONTAINER_SHADOW_WORKSPACE}/venv:${CHECKOUT_ROOT}/.venv"

    mkdir -p "${CHECKOUT_ROOT}/omd/build"
    mkdir -p "${CONTAINER_SHADOW_WORKSPACE}/omd_build"
    DOCKER_MOUNT_ARGS="${DOCKER_MOUNT_ARGS} -v ${CONTAINER_SHADOW_WORKSPACE}/omd_build:${CHECKOUT_ROOT}/omd/build"
fi

: "${CONTAINER_NAME:="ref-$(basename "$(pwd)")-$(sha1sum <<<"${CONTAINER_SHADOW_WORKSPACE}" | cut -c1-10)"}"

# Don't map ~/.cache but create a temporary folder inside the shadow workspace
# BEGIN COMMON CODE with docker_image_aliases_helper.groovy
if [ -e "${CONTAINER_SHADOW_WORKSPACE}/cache" ]; then
    # Bazel creates files without write permission
    chmod -R a+w "${CONTAINER_SHADOW_WORKSPACE}/cache"
fi
rm -rf "${CONTAINER_SHADOW_WORKSPACE}"
mkdir -p "${CONTAINER_SHADOW_WORKSPACE}/home"
mkdir -p "${CONTAINER_SHADOW_WORKSPACE}/home/.cache"
mkdir -p "${CONTAINER_SHADOW_WORKSPACE}/cache"
mkdir -p "${CHECKOUT_ROOT}/shared_cargo_folder"
mkdir -p "${CONTAINER_SHADOW_WORKSPACE}/home/$(realpath -s --relative-to="${HOME}" "${CHECKOUT_ROOT}")"
mkdir -p "${CONTAINER_SHADOW_WORKSPACE}/home/$(realpath -s --relative-to="${HOME}" "${GIT_COMMON_DIR}")"
# END COMMON CODE with docker_image_aliases_helper.groovy

# Needed for .cargo which is shared between workspaces
mkdir -p "${HOME}/shared_cargo_folder"

# UNCONDITIONAL MOUNTS
DOCKER_MOUNT_ARGS="-v ${CONTAINER_SHADOW_WORKSPACE}/home:${HOME}"
DOCKER_MOUNT_ARGS="${DOCKER_MOUNT_ARGS} -v ${CONTAINER_SHADOW_WORKSPACE}/cache:${HOME}/.cache"
DOCKER_MOUNT_ARGS="${DOCKER_MOUNT_ARGS} -v ${HOME}/shared_cargo_folder:${CHECKOUT_ROOT}/shared_cargo_folder"
DOCKER_MOUNT_ARGS="${DOCKER_MOUNT_ARGS} -v ${CHECKOUT_ROOT}:${CHECKOUT_ROOT}"
DOCKER_MOUNT_ARGS="${DOCKER_MOUNT_ARGS} -v ${GIT_COMMON_DIR}:${GIT_COMMON_DIR}"

if [ -d "${HOME}/.docker" ]; then
    mkdir -p "${CONTAINER_SHADOW_WORKSPACE}/home/.docker"
    DOCKER_MOUNT_ARGS="${DOCKER_MOUNT_ARGS} -v ${HOME}/.docker:${HOME}/.docker"
fi

# We're using git reference clones, see also jenkins/global-defaults.yml in checkmk_ci.
# That's why we need to mount the reference repos.
GIT_REFERENCE_CLONE_PATH="${HOME}/git_reference_clones/check_mk.git"
if [ -d "${GIT_REFERENCE_CLONE_PATH}" ]; then
    mkdir -p "${CONTAINER_SHADOW_WORKSPACE}/home/$(realpath -s --relative-to="${HOME}" "${GIT_REFERENCE_CLONE_PATH}")"
    DOCKER_MOUNT_ARGS="${DOCKER_MOUNT_ARGS} -v ${GIT_REFERENCE_CLONE_PATH}:${GIT_REFERENCE_CLONE_PATH}:ro"
fi

: "${IMAGE_ID:="$(
    if [ -n "${IMAGE_ALIAS}" ]; then
        "${CHECKOUT_ROOT}"/buildscripts/docker_image_aliases/resolve.py "${IMAGE_ALIAS}"
    else
        "${CHECKOUT_ROOT}"/defines/dev-images/reference-image-id
    fi
)"}"

: "${TERMINAL_FLAG:="$([ -t 0 ] && echo ""--interactive --tty"" || echo "")"}"

if [ -t 0 ]; then
    echo "Running in Docker container from image ${IMAGE_ID} (cmd=${CMD}) (workdir=${PWD})"
fi

# shellcheck disable=SC2086
docker run -a stdout -a stderr \
    --rm \
    --name $CONTAINER_NAME \
    ${TERMINAL_FLAG} \
    --init \
    -u "$(id -u):$(id -g)" \
    ${DOCKER_MOUNT_ARGS} \
    -v "/var/run/docker.sock:/var/run/docker.sock" \
    -v "/etc/passwd:/etc/passwd:ro" \
    -v "/etc/group:/etc/group:ro" \
    --group-add="$(getent group docker | cut -d: -f3)" \
    -e USER \
    -e CI \
    -e BANDIT_OUTPUT_ARGS \
    -e GROOVYLINT_OUTPUT_ARGS \
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
    -e GCC_TOOLCHAIN \
    -e DOCKER_REGISTRY_NO_HTTPS \
    -w "${PWD}" \
    ${DOCKER_RUN_ADDOPTS} \
    "${IMAGE_ID}" \
    sh -c "${CMD}"

ROOT_ARTIFACTS=$(find . -user root)
if [ -n "${ROOT_ARTIFACTS}" ]; then
    echo >&2 "WARNING: there are files/directories owned by root:"
    echo >&2 "${ROOT_ARTIFACTS}"
fi
