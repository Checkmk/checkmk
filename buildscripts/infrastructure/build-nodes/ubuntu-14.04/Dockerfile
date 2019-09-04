FROM ubuntu:14.04

SHELL ["/bin/bash", "-c"]
ENV DEBIAN_FRONTEND=noninteractive

RUN apt-get update \
    && apt-get install -y \
    apache2 \
    apache2-threaded-dev \
    build-essential \
    dietlibc-dev \
    dnsutils \
    dpatch \
    flex \
    gettext \
    git-buildpackage \
    libboost-all-dev \
    libcurl4-openssl-dev \
    libevent-dev \
    libffi-dev \
    libgd2-xpm-dev \
    libglib2.0-dev \
    libgnutls-dev \
    libldap2-dev \
    libltdl-dev \
    libmcrypt-dev \
    libmysqlclient15-dev \
    libncurses5-dev \
    libpango1.0-dev \
    libpcap-dev \
    libperl-dev \
    libpq-dev \
    libradiusclient-ng-dev \
    libreadline-dev \
    librrd-dev \
    libsqlite3-dev \
    libssl-dev \
    libxml2-dev \
    openssh-client \
    patch \
    rpcbind \
    smbclient \
    texinfo \
    tk-dev \
    uuid-dev \
    && rm -rf /var/lib/apt/lists/*

COPY bw-build-gnu-toolchain.sh /usr/sbin
RUN bw-build-gnu-toolchain.sh -b
RUN mv /usr/bin/gcc /usr/bin/gcc-old \
    && ln -s /usr/local/bin/gcc-8 /usr/local/bin/gcc \
    && ln -s /usr/local/bin/gcc-8 /usr/local/bin/cc
