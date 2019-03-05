FROM centos:7

SHELL ["/bin/bash", "-c"]

ARG PACKAGES

RUN yum -y --enablerepo=extras install \
    epel-release \
    && yum -y install \
    curl \
    enchant \
    gcc \
    git \
    krb5-devel \
    make \
    mysql-devel \
    nodejs \
    npm \
    openldap-devel \
    python \
    python-devel \
    rrdtool-devel \
    sudo \
    which
RUN curl https://bootstrap.pypa.io/get-pip.py -o get-pip.py \
    && python get-pip.py
RUN pip install --upgrade setuptools \
    && pip install git+https://github.com/pypa/pipenv.git
RUN yum -y install \
    $PACKAGES \
    && yum clean all
