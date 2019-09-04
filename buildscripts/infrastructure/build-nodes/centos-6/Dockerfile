FROM centos:6

SHELL ["/bin/bash", "-c"]

RUN yum -y makecache \
    && yum -y install \
    bind-utils \
    boost-devel \
    centos-release-scl \
    compat-readline5 \
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
    rrdtool-devel \
    rsync \
    samba-client \
    sqlite-devel \
    texinfo \
    tk-devel \
    which \
    wget \
    && yum -y install devtoolset-7 \
    && yum clean all

COPY bw-build-gnu-toolchain.sh /usr/sbin
RUN source scl_source enable devtoolset-7 \ 
    && bw-build-gnu-toolchain.sh -b
