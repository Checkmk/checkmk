FROM nexus.lan.tribe29.com:5010/sles-12sp4-base

SHELL ["/bin/bash", "-c"]

RUN zypper addrepo -G http://nexus:8081/repository/sles12sp4 sles12sp4 \
    && zypper -n in -y --force-resolution \
    awk \
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
    samba-client \
    sqlite3-devel \
    tar \
    texinfo \
    tk-devel \
    unzip \
    wget \
    which \
    && zypper clean -a

ARG ARTIFACT_STORAGE
COPY bw-build-gnu-toolchain.sh /usr/sbin
RUN bw-build-gnu-toolchain.sh -r $ARTIFACT_STORAGE -b
RUN cd /opt \
    && wget https://github.com/Kitware/CMake/releases/download/v3.15.4/cmake-3.15.4-Linux-x86_64.tar.gz \
    && tar xf cmake-3.15.4-Linux-x86_64.tar.gz \
    && ln -s /opt/cmake-3.15.4-Linux-x86_64/bin/* /usr/bin/

# New packages that are not needed for the build toolchain above should be added here.
# We avoid rebuild of the whole previous steps this way
RUN zypper -n in -y --force-resolution \
    chrpath \
    && zypper clean -a
