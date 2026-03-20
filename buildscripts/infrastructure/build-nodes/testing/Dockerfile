# rm -rf temp-build-context
# mkdir temp-build-context
# defines/dev-images/populate-build-context.sh temp-build-context
#
# docker build \
# --build-arg IMAGE_BASE='artifacts.lan.tribe29.com:4000/ubuntu-22.04:master-latest' \
# --build-arg DISTRO='ubuntu-22.04' \
# --tag testing-ubuntu-checkmk-master \
# -f buildscripts/infrastructure/build-nodes/testing/Dockerfile \
# temp-build-context
#
# docker run -it --rm \
# --cpus=4 --memory=8g \
# --workdir /checkmk \
# -v ./:/checkmk \
# --name testing-ubuntu \
# testing-ubuntu-checkmk-master:latest bash
#

ARG IMAGE_BASE
FROM ${IMAGE_BASE}

# these files are required to install everything on top of the parent image
# what is required to run the tests and builds specificly only possbile with
# this testing image
COPY \
    .bazelversion \
    defines.make \
    package_versions.bzl \
    build_lib.sh \
    Check_MK-pubkey.gpg \
    install-packer.sh \
    install-make-dist-deps.sh \
    install-lz4-parallel.sh \
    install-aws-cli.sh \
    strip_binaries \
    /opt/

# hack to use existing installation scripts, see CMK-20698
ENV \
    NEXUS_ARCHIVES_URL=" " \
    NEXUS_USERNAME=" " \
    NEXUS_PASSWORD=" "

# above image is ubuntu-22.04:master-latest
# docker inspect -f "{{ .Size }}" testing-ubuntu-checkmk-master:latest
# bash is required to be used in Jenkins with image.inside()
# curl is required to download artifacts
# cmake is required to install iwyu
# git is required to use tests and install iwyu
# gpg is required to use installation scripts
# libaio1 is required by mk-oracle component testing
# lsb-release is required to use installation scripts
# libenchant-2-dev is required to build the software architecture due to sphinxcontrib.spelling
# make is required for installations
# sudo is required to install packer
# unzip is required to install aws-cli
# wget is required to download artifacts
RUN apt-get update && \
    apt-get install -y \
        bash \
        cmake \
        curl \
        git \
        gpg \
        libaio1 \
        lsb-release \
        libenchant-2-dev \
        make \
        sudo \
        unzip \
        wget && \
    rm -rf /var/cache/apt/*

RUN /opt/install-make-dist-deps.sh
RUN /opt/install-packer.sh
RUN /opt/install-aws-cli.sh

# lz4 is required to tar home cache folder
RUN /opt/install-lz4-parallel.sh

RUN rm /opt/install*.sh /opt/defines.make /opt/.bazelversion /opt/package_versions.bzl /opt/build_lib.sh /opt/strip_binaries

# The file "/etc/ci.bazelrc" is already populated by the parent image

LABEL \
    com.checkmk.image_type="testing-image"

# entrypoint is already provided by the parent image
