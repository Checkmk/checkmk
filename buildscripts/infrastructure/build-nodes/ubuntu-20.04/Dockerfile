FROM ubuntu:20.04

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
    libgnutls28-dev \
    libgsf-1-dev \
    libkrb5-dev \
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
    && rm -rf /var/lib/apt/lists/*

ARG ARTIFACT_STORAGE

COPY bw-build-gnu-toolchain.sh /usr/sbin
RUN bw-build-gnu-toolchain.sh -r $ARTIFACT_STORAGE -b
RUN cd /opt \
    && wget https://github.com/Kitware/CMake/releases/download/v3.16.2/cmake-3.16.2-Linux-x86_64.tar.gz \
    && tar xf cmake-3.16.2-Linux-x86_64.tar.gz \
    && ln -s /opt/cmake-3.16.2-Linux-x86_64/bin/* /usr/bin/

# New packages that are not needed for the build toolchain above should be added here.
# We avoid rebuild of the whole previous steps this way
RUN apt-get update \
    && apt-get install -y \
    chrpath \
    joe \
    iputils-ping \
    vim \
    python3-importlib-metadata \
    && rm -rf /var/lib/apt/lists/*

ARG VERS_TAG
RUN echo $VERS_TAG > /version.txt
