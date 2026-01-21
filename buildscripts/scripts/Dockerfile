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
ARG IMAGE_BASE
FROM ${IMAGE_BASE}
# above image is python:3.12-alpine3.21

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
    "checkmk-dev-tools==2.0.2" \
    "pyyaml==6.0.2"

# verify installation
RUN cmk-dev info
