# docker build \
# --build-arg IMAGE_BASE=$(buildscripts/docker_image_aliases/resolve.py IMAGE_UBUNTU_24_04) \
# --tag minimal-ubuntu-checkmk-master \
# -f buildscripts/infrastructure/build-nodes/minimal/Dockerfile .
#
# docker run -it --rm \
# --workdir /checkmk \
# -v ./:/checkmk \
# -v /var/run/docker.sock:/var/run/docker.sock \
# --user ubuntu
# --name ubuntu-minimal \
# minimal-ubuntu-checkmk-master:latest bash
#

ARG IMAGE_BASE
FROM ${IMAGE_BASE}
# above image is ubuntu-24.04:master-latest
# docker inspect -f "{{ .Size }}" minimal-ubuntu-checkmk-master:latest
# 1460MB (1460664040)
# bash is required to be used in Jenkins with image.inside(), requires +0MB
# curl is required to download artifacts, requires +15MB
# git is required to use tests, requires +83MB
# gpg is required to use installation scripts, requires +13MB
# jq is required to parse bazel log files, requires +MB
# lsb-release is required to use installation scripts, requires +4MB
# make is required by tests, requires +47MB
# rsync is required to upload artifacts, requires +1MB
# python3 is required by tests, requires +19MB
# vim-tiny is required for convenience, requires +20MB
# wget is required to download artifacts, requires +1MB
RUN apt-get update && \
    apt-get install -y bash curl git gpg jq lsb-release make python3 rsync vim-tiny wget && \
    rm -rf /var/cache/apt/*

# bazelisk and bazel are basic tools for running tests, requires +77MB
COPY \
    .bazelversion \
    defines.make \
    package_versions.bzl \
    buildscripts/infrastructure/build-nodes/scripts/build_lib.sh \
    buildscripts/infrastructure/build-nodes/scripts/install-bazel.sh \
    buildscripts/infrastructure/build-nodes/scripts/install-docker.sh \
    buildscripts/infrastructure/build-nodes/scripts/install-nodejs.sh \
    /opt/

# hack to use existing installation scripts, see CMK-20698
ENV \
    NEXUS_ARCHIVES_URL=" " \
    NEXUS_USERNAME=" " \
    NEXUS_PASSWORD=" "

# no doubt this is needed
RUN /opt/install-bazel.sh

# nodejs, npm is required to run cmk-[frontend-vue, shared-typing, frontend], default npm version is not compatible, requires +184MB
RUN /opt/install-nodejs.sh

# docker is required to run test-agent-plugin, requires +480MB
RUN DISTRO="ubuntu-24.04" /opt/install-docker.sh

RUN rm /opt/*.sh /opt/defines.make /opt/.bazelversion

# required to run tests with bazel, requires +577MB
# libkrb5-dev, libldap2-dev, libsasl2-dev is required to build python-ldap
# libpq-dev is required to build psycopg2-binary
# libpcap-dev is required to build packages/cmc
# gawk is required to run test-agent-plugin, sw-documentation
# python3-enchant is required to run sw-documentation
# apache2 is required to run test-unit-omdlib
RUN apt-get update && \
    apt-get install -y apache2 gawk g++-13 libglib2.0-dev libkrb5-dev libldap2-dev libpango1.0-dev libpng-dev libpq-dev libsasl2-dev libpcap-dev libxml2-dev python3-enchant && \
    rm -rf /var/cache/apt/*

# gcc is not found within bazel actions otherwise
RUN update-alternatives --install "/usr/bin/gcc" gcc "/usr/bin/gcc-13" 100

# bazel can only be used as user, not as root https://github.com/bazelbuild/rules_python/pull/713
# USER ubuntu

# verify installation?
