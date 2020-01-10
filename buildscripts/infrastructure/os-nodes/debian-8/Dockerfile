FROM debian:8

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
    && pip install https://github.com/smokey42/pipenv/archive/last-checked.tar.gz \
    && rm -rf /var/lib/apt/lists/*
RUN pip uninstall -y pipenv \
    && pip install https://github.com/smokey42/pipenv/archive/last-checked.tar.gz

RUN rm -rf /bin/systemctl \
    && ln -s /bin/true /bin/systemctl

ARG VERS_TAG
RUN echo $VERS_TAG > /version.txt
