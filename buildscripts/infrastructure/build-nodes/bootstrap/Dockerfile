# docker build \
# --build-arg IMAGE_BASE=$(buildscripts/docker_image_aliases/resolve.py IMAGE_ALPINE_3_22) \
# --tag minimal-alpine-bash-git \
# -f buildscripts/infrastructure/build-nodes/bootstrap/Dockerfile .
#
# docker run -it --rm \
# --workdir /checkmk \
# -v ./:/checkmk \
# -v /var/run/docker.sock:/var/run/docker.sock \
# --name alpine322 \
# minimal-alpine-bash-git:latest bash
#

ARG IMAGE_BASE
FROM ${IMAGE_BASE}
# above image is alpine:3.22
# docker inspect -f "{{ .Size }}" minimal-ubuntu-checkmk-master:latest
# 29.8MB (29841300)
# bash is required to be used in Jenkins with image.inside(), requires +3MB
# git is required to performe clone operation, requires +13MB
# openssh is required to perform clone operation, requires +7MB
# make is required to get the safe branch name, requires +1MB
# cache removal saves 3MB
RUN apk update && \
    apk add bash git openssh make && \
    rm -rf /var/cache/apk/*
