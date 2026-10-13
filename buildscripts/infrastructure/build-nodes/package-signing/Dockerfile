# docker build \
# --build-arg IMAGE_BASE=$(buildscripts/docker_image_aliases/resolve.py IMAGE_UBUNTU_22_04) \
# --tag deb-package-signer \
# -f buildscripts/infrastructure/build-nodes/package-signing/Dockerfile .
#
# docker run -it --rm \
# --workdir /checkmk \
# -v ./:/checkmk \
# -v /var/run/docker.sock:/var/run/docker.sock \
# deb-package-signer:latest bash
#

ARG IMAGE_BASE=you_forgot_to_set:base_build_image

FROM ${IMAGE_BASE}
# kaniko is based on alpine, only shipping /bin/sh instead of /bin/bash
SHELL ["/bin/sh", "-c"]
ENV \
    DEBIAN_FRONTEND=noninteractive \
    LC_ALL=C.UTF-8 \
    LANG=C.UTF-8

# needed because of later installs and apt-cache get's purged
RUN apt-get update

# dpkg-sig is required to sign packages, only available until Ubuntu 22.04, see CMK-24094
# msitools is required for msiinfo in test source package at test_files.py
RUN apt-get update && \
    apt-get install -y dpkg-sig msitools && \
    rm -rf /var/cache/apt/*
