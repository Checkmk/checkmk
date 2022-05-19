FROM ubuntu:20.04

SHELL ["/bin/bash", "-c"]
ENV DEBIAN_FRONTEND=noninteractive
ENV LC_ALL=C.UTF-8
ENV LANG=C.UTF-8

ARG PACKAGES

RUN apt-get update \
    && apt-get install -y \
    gdebi \
    git \
    libenchant1c2a \
    libkrb5-dev \
    libldap2-dev \
    libmysqlclient-dev \
    librrd-dev \
    libsasl2-dev \
    libssl-dev \
    make \
    nullmailer \
    python-dev \
    python-dev \
    python3-pip \
    rrdtool \
    strace \
    sudo \
    vim \
    python3-importlib-metadata \
    && pip3 install --upgrade setuptools \
    && pip3 install git+https://github.com/pypa/pipenv.git@v2020.6.2 \
    && curl -sL https://deb.nodesource.com/setup_12.x | bash - \
    && apt-get install -y nodejs \
    && apt-get install -y \
    $PACKAGES \
    && rm -rf /var/lib/apt/lists/*

RUN rm -rf /bin/systemctl \
    && ln -s /bin/true /bin/systemctl

# New packages that are not needed for the build toolchain above should be added here.
# We avoid rebuild of the whole previous steps this way
RUN apt-get update \
    && apt-get install -y \
    joe \
    iputils-ping \
    vim \
    && rm -rf /var/lib/apt/lists/*

ARG VERS_TAG
RUN echo $VERS_TAG > /version.txt
