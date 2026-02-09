# rm -rf temp-build-context
# mkdir temp-build-context
# defines/dev-images/populate-build-context.sh temp-build-context
#
# docker build \
# --build-arg IMAGE_BASE='artifacts.lan.tribe29.com:4000/ubuntu-22.04:2.5.0-latest' \
# --build-arg DISTRO='ubuntu-22.04' \
# --tag testing-ubuntu-checkmk-2.5.0 \
# -f buildscripts/infrastructure/build-nodes/testing/Dockerfile \
# temp-build-context
#
# docker run -it --rm \
# --cpus=4 --memory=8g \
# --workdir /checkmk \
# -v ./:/checkmk \
# --name testing-ubuntu \
# testing-ubuntu-checkmk-2.5.0:latest bash
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
    install-iwyu.sh \
    install-clang.sh \
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

# above image is ubuntu-22.04:2.5.0-latest
# docker inspect -f "{{ .Size }}" testing-ubuntu-checkmk-2.5.0:latest
# 3849MB (3849192841)
# bash is required to be used in Jenkins with image.inside(), requires +0MB
# curl is required to download artifacts, requires +0MB
# cmake is required to install iwyu, requires +34MB
# git is required to use tests and install iwyu, requires +0MB
# gpg is required to use installation scripts, requires +0MB
# libaio1 is required by mk-oracle
# lsb-release is required to use installation scripts, requires +0MB
# make is required for installations, requires +0MB
# mbuffer is required for faster decompression with lz4, requires +1MB
# sudo is required to install packer, requires +0MB
# unzip is required to install aws-cli, requires +0MB
# wget is required to download artifacts, requires +0MB
RUN apt-get update && \
    apt-get install -y \
        bash \
        cmake \
        curl \
        git \
        gpg \
        libaio1 \
        lsb-release \
        make \
        mbuffer \
        sudo \
        unzip \
        wget && \
    rm -rf /var/cache/apt/*

# +5MB
RUN /opt/install-make-dist-deps.sh

# +1242MB
RUN /opt/install-clang.sh

# +48MB
RUN /opt/install-packer.sh

# +195MB
RUN /opt/install-aws-cli.sh

# lz4 is required to tar home cache folder, requires +1MB
RUN /opt/install-lz4-parallel.sh

RUN rm /opt/install*.sh /opt/defines.make /opt/.bazelversion /opt/package_versions.bzl /opt/build_lib.sh /opt/strip_binaries

# The file "/etc/ci.bazelrc" is already populated by the parent image

LABEL \
    com.checkmk.image_type="testing-image"

# entrypoint is already provided by the parent image
