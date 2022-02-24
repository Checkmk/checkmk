#Use same pinned image as 2.0.0 branch uses to be in sync with mirror
#FROM registry.suse.com/suse/sle15:15.3
FROM artifacts.lan.tribe29.com:4000/sle15@sha256:64284bcccbda0781a4986348fd41d2f44c925848a8c8cdf82eb9fb0dde3db1cb

SHELL ["/bin/bash", "-c"]
ENV PATH="/opt/bin:${PATH}"

ARG ARTIFACT_STORAGE

RUN zypper addrepo -G ${ARTIFACT_STORAGE}/repository/sles15sp3 sles15sp3 \
    && zypper -n --no-gpg-checks in --replacefiles \
    gawk \
    && zypper -n --no-gpg-checks in --replacefiles \
    curl \
    cyrus-sasl-devel \
    enchant-devel \
    git \
    krb5-devel \
    make \
    nodejs14 \
    npm14 \
    openldap2-devel \
    python \
    python-devel \
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
    libmariadb-devel \
    libopenssl-devel \
    libpcap-devel \
    libpng16-devel \
    libtiff-devel \
    libtool \
    libuuid-devel \
    libvpx-devel \
    libxml2-devel \
    make \
    mariadb-client \
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
