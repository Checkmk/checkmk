FROM nexus.lan.tribe29.com:4000/sles-12sp4-base

SHELL ["/bin/bash", "-c"]

ARG PACKAGES

RUN zypper addrepo -G http://nexus:8081/repository/sles12sp4 sles12sp4 \
    && zypper addrepo -G http://nexus:8081/repository/sles12spx-web-scripting web-scripting \
    && zypper -n --no-gpg-checks in --replacefiles \
    gawk \
    && zypper -n --no-gpg-checks in --replacefiles \
    curl \
    cyrus-sasl-devel \
    enchant-devel \
    git \
    krb5-devel \
    libmysqlclient-devel \
    make \
    nodejs10 \
    npm10 \
    openldap2-devel \
    python \
    python-devel \
    python-pyOpenSSL \
    python-xml \
    rrdtool-devel \
    sudo
RUN curl https://bootstrap.pypa.io/get-pip.py -o get-pip.py \
    && python get-pip.py
RUN pip install --upgrade setuptools \
    && pip install git+https://github.com/svenpanne/pipenv.git@41f30d7ac848fdfe3eb548ddd19b731bfa8c331a \
    && zypper -n --no-gpg-checks in --replacefiles \
    $PACKAGES \
    && zypper clean -a
