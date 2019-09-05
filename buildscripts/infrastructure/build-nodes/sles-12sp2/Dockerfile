FROM nexus.lan.tribe29.com:4000/sles-12sp2-base

SHELL ["/bin/bash", "-c"]

RUN zypper addrepo -G http://nexus:8081/repository/sles12sp2 sles12sp2 \
    && zypper ref -s \
    && zypper -n in -y --force-resolution \
    apache2-devel \
    bind-utils \
    boost-devel \
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
    rrdtool-devel \
    samba-client \
    sqlite3-devel \
    tar \
    texinfo \
    tk-devel \
    unzip \
    wget \
    which \
    && zypper clean -a

COPY bw-build-gnu-toolchain.sh /usr/sbin
RUN bw-build-gnu-toolchain.sh -b
RUN rm /usr/bin/gcc /usr/bin/g++ \
    && ln -s /opt/gcc-8.2.0/bin/gcc-8 /usr/bin/gcc \
    && ln -s /opt/gcc-8.2.0/bin/g++-8 /usr/bin/g++
