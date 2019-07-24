FROM debian:7

SHELL ["/bin/bash", "-c"]
ENV DEBIAN_FRONTEND=noninteractive
ENV LC_ALL=C.UTF-8
ENV LANG=C.UTF-8

ARG PACKAGES

RUN apt-get update \
    && apt-get install -y \
    apt-transport-https \
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
    python \
    python-dev \
    python-dev \
    rrdtool \
    strace \
    vim \
    && curl https://bootstrap.pypa.io/get-pip.py -o get-pip.py \
    && python get-pip.py \
    && rm get-pip.py \
    && pip install --upgrade setuptools \
    && pip install git+https://github.com/svenpanne/pipenv.git@41f30d7ac848fdfe3eb548ddd19b731bfa8c331a \
    && curl -sSL https://deb.nodesource.com/gpgkey/nodesource.gpg.key | sudo apt-key add - \
    && VERSION=node_11.x; DISTRO=jessie; echo "deb https://deb.nodesource.com/$VERSION $DISTRO main" | tee /etc/apt/sources.list.d/nodesource.list \
    && VERSION=node_11.x; DISTRO=jessie; echo "deb-src https://deb.nodesource.com/$VERSION $DISTRO main" | tee -a /etc/apt/sources.list.d/nodesource.list \
    && apt-get update \
    && apt-get install -y nodejs \
    && apt-get install -y \
    $PACKAGES \
    && rm -rf /var/lib/apt/lists/*

RUN rm -rf /bin/systemctl \
    && ln -s /bin/true /bin/systemctl
