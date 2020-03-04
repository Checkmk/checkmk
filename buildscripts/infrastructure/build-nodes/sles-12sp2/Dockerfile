ARG DOCKER_REGISTRY
FROM ${DOCKER_REGISTRY}/sles-12sp2-base

SHELL ["/bin/bash", "-c"]

ARG ARTIFACT_STORAGE

RUN zypper addrepo -G ${ARTIFACT_STORAGE}/repository/sles12sp2 sles12sp2 \
    && zypper ref -s \
    && zypper -n in -y --force-resolution \
    apache2-devel \
    bind-utils \
    curl \
    flex \
    freeradius-client-devel \
    freetype2-devel \
    gcc \
    gcc-c++ \
    gd-devel \
    git \
    glib2-devel \
    groff \
    krb5-devel \
    libXpm-devel \
    libbz2-devel \
    libcurl-devel \
    libevent-devel \
    libexpat-devel \
    libffi-devel \
    libgnutls-devel \
    libgsf-devel \
    libjpeg62-devel \
    libltdl7 \
    libmysqlclient-devel \
    libopenssl-devel \
    libpcap-devel \
    libpng16-devel \
    libtiff-devel \
    libtool \
    libuuid-devel \
    libvpx-devel \
    libxml2-devel \
    make \
    mysql \
    openldap2-devel \
    openssh \
    pango-devel \
    patch \
    postgresql-devel \
    readline-devel \
    rpcbind \
    rpm-build \
    rpm-devel \
    samba-client \
    sqlite3-devel \
    tar \
    texinfo \
    tk-devel \
    unzip \
    wget \
    which \
    chrpath \
    joe \
    iputils \
    vim \
    && zypper clean -a

# Install our standard tool chain for building
# - gnu-toolchain is needed for compiling all the C++ stuff
# - cmake is needed for e.g. building re2
# - openssl is needed by Python 3.7+
# - python is needed by our build / test chain
ARG ARTIFACT_STORAGE
ARG NEXUS_ARCHIVES_URL
ARG NEXUS_USERNAME
ARG NEXUS_PASSWORD
ARG DISTRO
ARG BRANCH_VERSION
COPY scripts/* /opt/
RUN export NEXUS_ARCHIVES_URL="$NEXUS_ARCHIVES_URL" \
    NEXUS_USERNAME="$NEXUS_USERNAME" \
    NEXUS_PASSWORD="$NEXUS_PASSWORD" \
    BRANCH_VERSION="$BRANCH_VERSION" \
    DISTRO="$DISTRO" \
    && /opt/install-gnu-toolchain.sh \
    && /opt/install-cmake.sh \
    && /opt/install-openssl.sh \
    && /opt/install-python.sh \
    && rm -rf /opt/src

ARG VERS_TAG
RUN echo $VERS_TAG > /version.txt
