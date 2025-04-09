# docker build \
# --tag minimal-alpine-checkmk-ci-2.4.0 \
# -f buildscripts/scripts/Dockerfile .
#
# docker run -it --rm \
# --workdir /checkmk \
# -v ./:/checkmk \
# --name alpine321 \
# minimal-alpine-checkmk-ci-2.4.0:latest bash
#

FROM artifacts.lan.tribe29.com:4000/python@sha256:1e5c1003284738564008fec60124f2a1a81bfda5b872bf334467ed8689783b18
# 119MB
# alpine:3.21 around 190MB
# python:3.11.6-slim around 1100MB

# bash is required to be used in Jenkins with image.inside(), requires +3MB
# git is required to use checkmk-dev-tools, requires +13MB
# make is required by scripts/fake-artifacts, see CMK-21338, requires +9MB
# coreutils, grep is required by validate_changes.py/find-[python,shell]-files
# to get "sort --zero-terminated" and "grep --binary-files=", requires +2MB
# cache removal saves 3MB
RUN apk update && \
    apk add bash git make coreutils grep && \
    rm -rf /var/cache/apk/*

# install checkmk-dev-tools to run ci-artifacts
# install pyyaml to parse editions.yml and stages.yml
RUN pip3 install --break-system-packages \
 "checkmk-dev-tools>=0.4.3" \
 pyyaml

# verify installation
RUN cmk-dev info
