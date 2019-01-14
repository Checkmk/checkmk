FROM centos:6

SHELL ["/bin/bash", "-c"]

RUN yum -y makecache \
 \
    && yum -y install \
    boost-devel \
    curl-devel \
    expat-devel \
    bind-utils \
    gcc \
    gcc-c++ \
    libevent-devel \
    libtool-ltdl-devel \
    libtool-ltdl \
    gd-devel \
    libXpm-devel \
    libjpeg-devel \
    httpd-devel \
    libmcrypt-devel \
    libxml2-devel \
    sqlite-devel \
    tk-devel \
    mysql-devel \
    postgresql-devel \
    ncurses-devel \
    openssl-devel \
    pango-devel \
    pcre-devel \
    patch \
    php \
    readline-devel \
    compat-readline5 \
    rpm-build \
    samba-client \
    rpcbind \
    libuuid-devel \
    which \
    perl-devel \
    perl-ExtUtils-Embed \
    perl-Time-HiRes \
    rsync \
    freeradius-devel \
    groff \
    pcre-devel \
    libpcap-devel \
    gettext \
    libgsf-devel \
    rrdtool-devel \
    libffi-devel \
    flex \
    openssh-clients \
    git \
    && yum clean all

RUN yum -y makecache \
 \
    && yum -y install \
    wget \
    && yum clean all

COPY bw-build-gnu-toolchain /usr/sbin
# Nasty, nasty workaround...
# This will be moved to a jenkinsfile to build containers
# to avoid cloning and packing the binutils too often
RUN cd /tmp/build-gcc-toolchain/ \
    && git clone git://sourceware.org/git/binutils-gdb.git \
    && cd binutils-gdb \
    && git reset --hard bb27775165d9b992120371383012404e213b1981 \
    && git clean -dfX \
    && ./src-release.sh -x binutils \
    && cd .. \
    && ln -s binutils-gdb/binutils-2.31.51.tar.xz binutils-2.31.1.tar.xz

RUN bw-build-gnu-toolchain
RUN mv /usr/bin/gcc /usr/bin/gcc-4 \
    && ln -s /usr/local/bin/gcc-8 /usr/local/bin/gcc \
    && ln -s /usr/local/bin/gcc-8 /usr/local/bin/cc
