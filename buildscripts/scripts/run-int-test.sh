#!/usr/bin/env bash

export RESULTS_DIR="$WORKSPACE/results"
mkdir -p "$RESULTS_DIR"
rm -rf "$RESULTS_DIR/"*

export BRANCH="2.0.0"
export CMK_VERSION="${BRANCH}-$(date "+%F" | tr - .)"
PKG_URL="https://download.checkmk.com/checkmk/${CMK_VERSION}/check-mk-enterprise-${CMK_VERSION}_0.buster_amd64.deb"

echo "CMK_VERSION:$CMK_VERSION"
echo "PKG_URL:$PKG_URL"

cd "$WORKSPACE/check_mk"
(cd docker; curl -O -u "$(cat ~/.cmk-credentials)" "$PKG_URL")

#    -e HOME \
#    -e WORKSPACE \

DOCKER_RUN_ADDOPTS="\
    --network=host \
    -e BRANCH \
    -v /var/run/docker.sock:/var/run/docker.sock \
    -v $WORKSPACE:$WORKSPACE \
    -v $HOME/.cmk-credentials:$HOME/.cmk-credentials:ro \
    -v $HOME/.docker/config.json:$HOME/.docker/config.json:ro \
    " \
IMAGE_ID="artifacts.lan.tribe29.com:4000/ubuntu-20.04:2.0.0-latest" \
PYTEST_ADDOPTS="--junitxml='$RESULTS_DIR/junit.xml'" \
scripts/run-in-docker.sh make -C tests test-docker

