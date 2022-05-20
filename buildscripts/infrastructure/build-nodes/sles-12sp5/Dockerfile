FROM registry.suse.com/suse/sles12sp5

SHELL ["/bin/bash", "-c"]
ENV PATH="/opt/bin:${PATH}"

ARG ARTIFACT_STORAGE

RUN zypper addrepo -G ${ARTIFACT_STORAGE}/repository/sles12sp5 sles12sp5 \
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

RUN zypper ref -s \
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

ARG ARTIFACT_STORAGE
COPY bw-build-gnu-toolchain.sh /usr/sbin
RUN bw-build-gnu-toolchain.sh -r $ARTIFACT_STORAGE -b
RUN cd /opt \
    && wget https://github.com/Kitware/CMake/releases/download/v3.16.2/cmake-3.16.2-Linux-x86_64.tar.gz \
    && tar xf cmake-3.16.2-Linux-x86_64.tar.gz \
    && ln -s /opt/cmake-3.16.2-Linux-x86_64/bin/* /usr/bin/

ARG VERS_TAG
RUN echo $VERS_TAG > /version.txt
