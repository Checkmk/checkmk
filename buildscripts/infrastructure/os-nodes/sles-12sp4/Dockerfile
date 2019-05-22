FROM nexus.lan.tribe29.com:5010/sles-12sp4-base

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
    && pip install git+https://github.com/pypa/pipenv.git@c67a38e9203ad454a04516253ee626217b1364bc \
    && zypper -n --no-gpg-checks in --replacefiles \
    $PACKAGES \
    && zypper clean -a
