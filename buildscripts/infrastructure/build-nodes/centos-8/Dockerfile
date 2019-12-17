FROM centos:centos8

SHELL ["/bin/bash", "-c"]

RUN yum -y makecache \
    && yum -y --enablerepo=PowerTools install \
    bind-utils \
    boost-devel \
    curl-devel \
    expat-devel \
    flex \
    flex-devel \
    freeradius-devel \
    gcc \
    gcc-c++ \
    gd-devel \
    gettext \
    httpd-devel \
    isl-devel \
    kernel-headers \
    libXpm-devel \
    libdbi-devel \
    libevent-devel \
    libffi-devel \
    libgsf-devel \
    libiscsi-devel \
    libjpeg-devel \
    libmpc-devel \
    libpcap-devel \
    libstdc++-devel \
    libstdc++-static \
    libtool-ltdl \
    libtool-ltdl-devel \
    libuuid-devel \
    libxml2-devel \
    mariadb-devel \
    mpfr-devel \
    ncurses-devel \
    openssh-clients \ 
    openssl-devel \
    pango-devel \
    patch \
    pcre-devel \
    perl \
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
    && yum clean all
RUN yum -y makecache \
    && yum -y --enablerepo=PowerTools reinstall \
    kernel-headers \
    && yum clean all

#ARG ARTIFACT_STORAGE
#COPY bw-build-gnu-toolchain.sh /usr/sbin
#RUN bw-build-gnu-toolchain.sh -r $ARTIFACT_STORAGE -b
#
#RUN mv /usr/bin/gcc /usr/bin/gcc-old || true \
#    && mv /usr/bin/cc /usr/bin/cc-old || true \
#    && ln -s /usr/bin/gcc-8 /usr/bin/gcc \
#    && ln -s /usr/bin/gcc-8 /usr/bin/cc
RUN cd /opt \
    && wget https://github.com/Kitware/CMake/releases/download/v3.15.4/cmake-3.15.4-Linux-x86_64.tar.gz \
    && tar xf cmake-3.15.4-Linux-x86_64.tar.gz \
    && ln -s /opt/cmake-3.15.4-Linux-x86_64/bin/* /usr/bin/

# New packages that are not needed for the build toolchain above should be added here.
# We avoid rebuild of the whole previous steps this way
RUN yum -y makecache \
    && yum -y install \
        chrpath \
    && yum clean all
