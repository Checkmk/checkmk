FROM ubuntu:14.04

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
    librrd4 \
    libsasl2-dev \
    libssl-dev \
    make \
    nullmailer \
    python-dev \
    python-pip \
    rrdtool \
    strace \
    vim \
    && curl -sL https://deb.nodesource.com/setup_12.x | bash - \
    && apt-get install -y nodejs \
    && apt-get install -y \
    $PACKAGES \
    && pip install --upgrade pip \
    && pip install --upgrade setuptools \
    && pip install git+https://github.com/pypa/pipenv.git@2549656dc09e132d8ba2fa6327c939f5f9a951b7 \
    && rm -rf /var/lib/apt/lists/*
RUN pip uninstall -y pipenv \
    && pip install git+https://github.com/pypa/pipenv.git@2549656dc09e132d8ba2fa6327c939f5f9a951b7

RUN rm -rf /bin/systemctl \
    && ln -s /bin/true /bin/systemctl

# New packages that are not needed for the build toolchain above should be added here.
# We avoid rebuild of the whole previous steps this way
RUN apt-get update \
    && apt-get install -y \
    joe \
    vim \
    && rm -rf /var/lib/apt/lists/*

ARG VERS_TAG
RUN echo $VERS_TAG > /version.txt
