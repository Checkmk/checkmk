FROM registry.suse.com/suse/sle15:15.2

SHELL ["/bin/bash", "-c"]
ENV PATH="/opt/bin:${PATH}"

ARG ARTIFACT_STORAGE

# Need to install older version of multiple libs, since base image was updated
RUN zypper addrepo -G ${ARTIFACT_STORAGE}/repository/sles15sp2 sles15sp2 \
    && zypper in -f -y \
    libglib-2_0-0-2.62.5-1.26 \
    libmount1-2.33.1-4.5.1 \
    libpcre1-8.41-4.20 \
    libblkid1-2.33.1-4.5.1 \
    libuuid1-2.33.1-4.5.1 \
    libkeyutils1-1.5.10 \
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

RUN zypper ref -s \
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
    intltool \
    krb5-devel \
    libXpm-devel \
    libbz2-devel \
    libcurl-devel \
    libevent-devel \
    libexpat-devel \
    libffi-devel \
    libgnutls-devel \
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
    postgresql12-server-devel \
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
    iputils \
    vim \
    && zypper clean -a

ARG ARTIFACT_STORAGE
COPY bw-build-gnu-toolchain.sh /usr/sbin
RUN bw-build-gnu-toolchain.sh -r $ARTIFACT_STORAGE -b
RUN cd /opt \
    && wget https://github.com/Kitware/CMake/releases/download/v3.16.2/cmake-3.16.2-Linux-x86_64.tar.gz \
    && tar xf cmake-3.16.2-Linux-x86_64.tar.gz \
    && ln -s /opt/cmake-3.16.2-Linux-x86_64/bin/* /usr/bin/

ARG VERS_TAG
RUN echo $VERS_TAG > /version.txt
