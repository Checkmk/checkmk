#!/bin/bash
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# The test image is selected automatically, but can still be set via 
# enviroment. e.g. for master:
# export IMAGE_TESTING="artifacts.lan.tribe29.com:4000/ubuntu-20.04:master-latest"

set -ex
COMMAND=$@
REPO_DIR=$(git rev-parse --show-toplevel)
: "${IMAGE_TESTING:="$($REPO_DIR/buildscripts/docker_image_aliases/resolve.sh IMAGE_TESTING)"}"

echo "Running in Docker container from $IMAGE_TESTING (workdir $PWD)"

docker run -t -a stdout -a stderr \
    --rm \
    --init \
    -u "$UID:$(id -g)" \
    -v "$REPO_DIR:$REPO_DIR" \
    -v "/var/run/docker.sock:/var/run/docker.sock" \
    --group-add=$(getent group docker | cut -d: -f3) \
    -w "$PWD" \
    -e JUNIT_XML \
    -e PYLINT_ARGS \
    -e PYTEST_ADDOPTS \
    -e DOCKER_ADDOPTS \
    -e MYPY_ADDOPTS \
    -e PYTHON_FILES \
    -e RESULTS \
    -e WORKDIR \
    "$IMAGE_TESTING" \
    $COMMAND
