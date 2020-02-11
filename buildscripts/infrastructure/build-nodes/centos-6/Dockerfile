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
    && yum -y install devtoolset-7 \
    && yum clean all

ARG ARTIFACT_STORAGE
COPY bw-build-gnu-toolchain.sh /usr/sbin
RUN source scl_source enable devtoolset-7 \ 
    && bw-build-gnu-toolchain.sh -r $ARTIFACT_STORAGE -b

RUN cd /opt \
    && wget https://github.com/Kitware/CMake/releases/download/v3.16.2/cmake-3.16.2-Linux-x86_64.tar.gz \
    && tar xf cmake-3.16.2-Linux-x86_64.tar.gz \
    && ln -s /opt/cmake-3.16.2-Linux-x86_64/bin/* /usr/bin/

# New packages that are not needed for the build toolchain above should be added here.
# We avoid rebuild of the whole previous steps this way
RUN yum -y makecache \
    && yum -y install \
        chrpath \
    joe \
    vim \
    && yum clean all

ARG VERS_TAG
RUN echo $VERS_TAG > /version.txt
