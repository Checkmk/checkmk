FROM centos:7

SHELL ["/bin/bash", "-c"]

RUN yum -y makecache \
    && yum -y install \
    bind-utils \
    curl \
    curl-devel \
    expat-devel \
    flex \
    flex-devel \
    freeradius-devel \
    gcc \
    gcc-c++ \
    gd-devel \
    gettext \
    groff \
    httpd-devel \
    libXpm-devel \
    libdbi-devel \
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
    mariadb-devel \
    ncurses-devel \
    openssh-clients \
    openssl-devel \
    pango-devel \
    patch \
    pcre-devel \
    perl-ExtUtils-Embed \
    perl-IO-Zlib \
    perl-Locale-Maketext-Simple \
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
    wget \
    which \
    chrpath \
    joe \
    ping \
    vim \
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
