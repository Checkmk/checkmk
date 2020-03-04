FROM centos:6

SHELL ["/bin/bash", "-c"]

RUN yum -y makecache \
    && yum -y install \
    bind-utils \
    centos-release-scl \
    compat-readline5 \
    curl \
    curl-devel \
    expat-devel \
    flex \
    freeradius-devel \
    gcc \
    gcc-c++ \
    gd-devel \
    gettext \
    git \
    groff \
    httpd-devel \
    libXpm-devel \
    libevent-devel \
    libffi-devel \
    libgsf-devel \
    libjpeg-devel \
    libmcrypt-devel \
    libpcap-devel \
    libtool-ltdl \
    libtool-ltdl-devel \
    libuuid-devel \
    libxml2-devel \
    mysql-devel \
    ncurses-devel \
    openssh-clients \
    openssl-devel \
    pango-devel \
    patch \
    pcre-devel \
    pcre-devel \
    perl-ExtUtils-Embed \
    perl-Time-HiRes \
    perl-devel \
    php \
    postgresql-devel \
    readline-devel \
    rpcbind \
    rpm-build \
    rsync \
    samba-client \
    sqlite-devel \
    texinfo \
    tk-devel \
    which \
    wget \
    chrpath \
    joe \
    ping \
    vim \
    && yum -y install devtoolset-7 \
    && yum clean all

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
