ARG DOCKER_REGISTRY
FROM ${DOCKER_REGISTRY}/sles-12sp4-base

SHELL ["/bin/bash", "-c"]

ARG ARTIFACT_STORAGE
ARG PACKAGES

RUN zypper addrepo -G ${ARTIFACT_STORAGE}/repository/sles12sp4 sles12sp4 \
    && zypper addrepo -G ${ARTIFACT_STORAGE}/repository/sles12spx-web-scripting web-scripting \
    && zypper in -f -y \
    libpcre1-8.39-8.3.1 \
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
    sudo \
    && zypper clean -a
RUN curl https://bootstrap.pypa.io/pip/2.7/get-pip.py -o get-pip.py \
    && python get-pip.py
RUN pip install --upgrade setuptools \
    && pip install git+https://github.com/pypa/pipenv.git@v2020.6.2 \
    && zypper -n --no-gpg-checks in --replacefiles \
    $PACKAGES \
    && zypper clean -a

# New packages that are not needed for the build toolchain above should be added here.
# We avoid rebuild of the whole previous steps this way
RUN zypper ref \
    && zypper -n in -y --force-resolution \
    joe \
    iputils \
    vim \
    && zypper clean -a

ARG VERS_TAG
RUN echo $VERS_TAG > /version.txt
