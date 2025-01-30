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

FROM python:3.12-alpine3.21
# 111MB
# alpine:3.21 around 190MB
# python:3.11.6-slim around 1100MB

# bash is required to be used in Jenkins with image.inside(), requires +3MB
# git is required to use checkmk-dev-tools, requires +13MB
RUN apk update && apk add bash git make

# install checkmk-dev-tools
RUN pip3 install --break-system-packages \
 checkmk-dev-tools \
 pyyaml

# verify installation
RUN cmk-dev info
