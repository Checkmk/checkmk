FROM 10.9.1.101:4000/sles-11sp4-base

SHELL ["/bin/bash", "-c"]

RUN zypper addrepo -G http://10.9.1.101:8081/repository/sles11sp4  sles11sp4 \
    && zypper ref -s \
    && zypper -n in -y --force-resolution \
    boost-devel \
    curl \
    samba-client \
    freetype2-devel \
    gcc6 \
    gcc-c++ \
    gd-devel \
    git \
    glib-devel \
    libcurl-devel \
    libexpat-devel \
    libevent-devel \
    libgnutls-devel \
    libjpeg-devel \
    libmcrypt-devel \
    libmysqlclient-devel \
    postgresql94-devel \
    libopenssl-devel \
    libpng-devel \
    libuuid-devel \
    libxml2-devel \
    sqlite3-devel \
    tk-devel \
    make \
    openldap2-devel \
    pango-devel \
    pcre-devel \
    patch \
    readline-devel \
    apache2-devel \
    freeradius-client-devel \
    libtool \
    libtool \
    groff \
    ruby \
    tar \
    tcl-devel \
    gettext-tools \
    gettext \
    libbz2-devel \
    libpcap-devel \
    rrdtool-devel \
    libffi-devel \
    krb5-devel \
    flex \
    openssh \
    texinfo \
    wget \
    && zypper clean -a

COPY bw-build-gnu-toolchain.sh /usr/sbin
RUN bw-build-gnu-toolchain.sh -b

RUN rm /usr/bin/gcc /usr/bin/g++
