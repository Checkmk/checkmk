FROM ubuntu:18.04

ENV DEBIAN_FRONTEND=noninteractive

RUN apt-get update \
    && apt-get install -y \
    alien \
    apache2 \
    apache2-dev \
    autoconf \
    bear \
    bison \
    build-essential \
    chrpath \
    joe \
    vim \
    clang-7 \
    clang-format-7 \
    clang-tidy-7 \
    devscripts \
    direnv \
    dnsutils \
    doxygen \
    dpatch \
    dpkg-sig \
    enchant \
    expect \
    figlet \
    flex \
    g++ \
    gettext \
    git=1:2.17.0-1ubuntu1 \
    git-buildpackage \
    git-man=1:2.17.0-1ubuntu1 \
    ksh \
    libboost-all-dev \
    libboost-dev \
    libboost-system-dev \
    libclang-7-dev \
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
    libsasl2-dev \
    libsqlite3-dev \
    libterm-readkey-perl \
    libtool \
    libxml2-dev \
    llvm-7-dev \
    mono-complete \
    mono-xbuild \
    openssh-client \
    p7zip-full \
    patch \
    pngcrush \
    poedit \
    python-pip \
    python-polib \
    rpcbind \
    rpm \
    rsync \
    smbclient \
    texinfo \
    tk-dev \
    uuid-dev \
    valgrind \
    && rm -rf /var/lib/apt/lists/*

run curl -sL https://deb.nodesource.com/setup_12.x | bash - \
    && apt-get install -y nodejs \
    && rm -rf /var/lib/apt/lists/*

RUN pip install -U git+https://github.com/pypa/pipenv.git@v2020.6.2

RUN pip install \
    pathlib2 \
    typing \
    backports.functools_lru_cache

RUN apt-get update \
    && apt-get install -y \
    apt-transport-https \
    ca-certificates \
    curl \
    software-properties-common \
    && curl -fsSL https://download.docker.com/linux/ubuntu/gpg | apt-key add - \
    && add-apt-repository \
    "deb [arch=amd64] https://download.docker.com/linux/ubuntu \
    $(lsb_release -cs) \
    stable" \
    && apt-get update \
    && apt-get install -y \
    docker-ce \
    && rm -rf /var/lib/apt/lists/*

# Addd missing packages
RUN apt-get update \
    && apt-get install -y \
    iputils-ping \
    && rm -rf /var/lib/apt/lists/*
