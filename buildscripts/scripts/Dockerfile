# docker build \
# --tag minimal-alpine-checkmk-ci-master \
# -f buildscripts/scripts/Dockerfile .
#
# docker run -it --rm \
# --workdir /checkmk \
# -v ./:/checkmk \
# --name alpine321 \
# minimal-alpine-checkmk-ci-master:latest bash
#

FROM python:3.12-alpine3.21
# 120MB
# alpine:3.21 around 190MB
# python:3.11.6-slim around 1100MB

# bash is required to be used in Jenkins with image.inside(), requires +3MB
# git is required to use checkmk-dev-tools, requires +13MB
# make is required by scripts/fake-artifacts, see CMK-21338, requires +9MB
RUN apk update && apk add bash git make

# install checkmk-dev-tools to run ci-artifacts
# install pyyaml to parse editions.yml and stages.yml
RUN pip3 install --break-system-packages \
 "checkmk-dev-tools>=0.4.1" \
 pyyaml

# verify installation
RUN cmk-dev info
