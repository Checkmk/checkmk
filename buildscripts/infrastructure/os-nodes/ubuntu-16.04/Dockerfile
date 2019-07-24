FROM ubuntu:16.04

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
    python-dev \
    python3-pip \
    rrdtool \
    strace \
    vim \
    && pip3 install --upgrade setuptools \
    && pip3 install git+https://github.com/svenpanne/pipenv.git@41f30d7ac848fdfe3eb548ddd19b731bfa8c331a \
    && curl -sL https://deb.nodesource.com/setup_12.x | bash - \
    && apt-get install -y nodejs \
    && apt-get install -y \
    $PACKAGES \
    && rm -rf /var/lib/apt/lists/*

RUN rm -rf /bin/systemctl \
    && ln -s /bin/true /bin/systemctl
