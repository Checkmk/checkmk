#!/bin/bash
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# The test container should be set via the enviroment. e.g. for master:
# export TEST_CONTAINER="artifacts.lan.tribe29.com:4000/ubuntu-20.04:master-latest"

set -ex
COMMAND=$@
REPO_DIR=$(git rev-parse --show-toplevel)

if [ -e $TEST_CONTAINER ]; then
    echo "Please set TEST_CONTAINER via the environment:"
    echo "e.g.: export TEST_CONTAINER='artifacts.lan.tribe29.com:4000/ubuntu-20.04:master-latest'"
    exit 1
fi

echo "Running in Docker Container $TEST_CONTAINER (workdir $PWD)"
docker pull $TEST_CONTAINER
docker run -t -a stdout -a stderr \
    --init \
    -u "$UID:$UID" \
    -v "$REPO_DIR:$REPO_DIR" \
    -w "$PWD" \
    -e JUNIT_XML \
    -e PYLINT_ARGS \
    -e PYTEST_ADDOPTS \
    -e PYTHON_FILES \
    -e RESULTS \
    -e WORKDIR \
    "$TEST_CONTAINER" \
    $COMMAND
