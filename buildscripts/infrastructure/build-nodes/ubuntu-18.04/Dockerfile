FROM ubuntu:18.04

SHELL ["/bin/bash", "-c"]
ENV DEBIAN_FRONTEND=noninteractive

RUN apt-get update \
    && apt-get install -y \
    apache2 \
    apache2-dev \
    autoconf \
    bear \
    build-essential \
    chrpath \
    clang-6.0 \
    clang-format-6.0 \
    clang-tidy-6.0 \
    devscripts \
    direnv \
    dnsutils \
    doxygen \
    dpatch \
    enchant \
    figlet \
    flex \
    g++-8 \
    gettext \
    git-buildpackage \
    ksh \
    libboost-all-dev \
    libboost-dev \
    libboost-system-dev \
    libclang-6.0-dev \
    libcloog-ppl1 \
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
    librrd-dev \
    libsasl2-dev \
    libsqlite3-dev \
    libssl-dev \
    libtool \
    libxml2-dev \
    llvm-6.0-dev \
    openssh-client \
    p7zip-full \
    patch \
    pngcrush \
    poedit \
    python-pip \
    python-polib \
    rpcbind \
    rsync \
    slimit \
    smbclient \
    tk-dev \
    uuid-dev \
    valgrind \
    && rm -rf /var/lib/apt/lists/*

# For the common part, split later
RUN pip install pathlib2 \
    typing

RUN apt-get update \
    && apt-get install -y \
    rpm \
    alien \
    mono-xbuild \
    && rm -rf /var/lib/apt/lists/*

COPY bw-build-gnu-toolchain /usr/sbin
RUN bw-build-gnu-toolchain
