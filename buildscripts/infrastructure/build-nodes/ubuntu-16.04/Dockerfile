FROM ubuntu:16.04

SHELL ["/bin/bash", "-c"]
ENV DEBIAN_FRONTEND=noninteractive

RUN apt-get update \
    && apt-get install -y \
    apache2 \
    apache2-dev \
    autoconf \
    build-essential \
    devscripts \
    dnsutils \
    dpatch \
    flex \
    gettext \
    git-buildpackage \
    curl \
    libcurl4-openssl-dev \
    libevent-dev \
    libffi-dev \
    libfreeradius-dev \
    libgd-dev \
    libglib2.0-dev \
    libgnutls-dev \
    libgsf-1-dev \
    libldap2-dev \
    libltdl-dev \
    libmcrypt-dev \
    libmysqlclient-dev \
    libncurses5-dev \
    libpango1.0-dev \
    libpcap-dev \
    libperl-dev \
    libpq-dev \
    libreadline-dev \
    libsqlite3-dev \
    libssl-dev \
    libtool \
    libxml2-dev \
    openssh-client \
    patch \
    rpcbind \
    rsync \
    smbclient \
    texinfo \
    tk-dev \
    uuid-dev \
    chrpath \
    joe \
    iputils-ping \
    vim \
    && rm -rf /var/lib/apt/lists/*

# Install our standard tool chain for building
# - gnu-toolchain is needed for compiling all the C++ stuff
# - cmake is needed for e.g. building re2
# - openssl is needed by Python 3.7+
# - python is needed by our build / test chain
ARG ARTIFACT_STORAGE
ARG NEXUS_ARCHIVES_URL
ARG NEXUS_USERNAME
ARG NEXUS_PASSWORD
ARG DISTRO
ARG BRANCH_VERSION
COPY scripts/* /opt/
RUN export NEXUS_ARCHIVES_URL="$NEXUS_ARCHIVES_URL" \
    NEXUS_USERNAME="$NEXUS_USERNAME" \
    NEXUS_PASSWORD="$NEXUS_PASSWORD" \
    BRANCH_VERSION="$BRANCH_VERSION" \
    DISTRO="$DISTRO" \
    && /opt/install-gnu-toolchain.sh \
    && /opt/install-cmake.sh \
    && /opt/install-openssl.sh \
    && /opt/install-python.sh \
    && rm -rf /opt/src

ARG VERS_TAG
RUN echo $VERS_TAG > /version.txt
