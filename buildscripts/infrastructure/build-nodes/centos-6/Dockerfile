FROM centos:6

SHELL ["/bin/bash", "-c"]

# We need to set a fixed mirror, since Centos does not provide a mirror anymore:
RUN rm -f /etc/yum.repos.d/* \
    && echo '[base]' > /etc/yum.repos.d/base.repo \
    && echo 'name=Centos 6 mirror' >> /etc/yum.repos.d/base.repo \
    && echo 'baseurl=http://linuxsoft.cern.ch/centos-vault/6.10/os/x86_64/' >> /etc/yum.repos.d/base.repo \
    && echo 'gpgcheck=0' >> /etc/yum.repos.d/base.repo \
    && echo 'priority=1' >> /etc/yum.repos.d/base.repo \
    && echo ''  >> /etc/yum.repos.d/base.repo \
    && echo '[sclo-rh]' >> /etc/yum.repos.d/base.repo \
    && echo 'name=Centos 6 mirror' >> /etc/yum.repos.d/base.repo \
    && echo 'baseurl=https://repo.cloudlinux.com/cloudlinux/6.10/sclo/devtoolset-7/x86_64/' >> /etc/yum.repos.d/base.repo \
    && echo 'gpgcheck=0' >> /etc/yum.repos.d/base.repo

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
    ping \
    vim \
    && yum clean all

ARG VERS_TAG
RUN echo $VERS_TAG > /version.txt
