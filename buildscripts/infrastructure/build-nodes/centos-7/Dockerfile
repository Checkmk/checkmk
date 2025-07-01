ARG IMAGE_CENTOS_7
# hadolint ignore=DL3006
FROM ${IMAGE_CENTOS_7} AS base

SHELL ["/bin/bash", "-c"]
ENV PATH="/opt/bin:${PATH}"

# CentOS-7 is deprecated since 2024-07-01
RUN sed -i s/mirror.centos.org/vault.centos.org/g /etc/yum.repos.d/*.repo
RUN sed -i s/^#.*baseurl=http/baseurl=http/g /etc/yum.repos.d/*.repo
RUN sed -i s/^mirrorlist=http/#mirrorlist=http/g /etc/yum.repos.d/*.repo

RUN yum -y --enablerepo=extras install \
    epel-release

# Special handling for epel*.repo
RUN sed -i 's/metalink=/#metalink=/g' /etc/yum.repos.d/epel*
RUN sed -i 's|^#.*baseurl=http|baseurl=http|g' /etc/yum.repos.d/epel*

RUN sed -i 's|baseurl=http://download.fedoraproject.org/pub/epel/7/$basearch|baseurl=https://archives.fedoraproject.org/pub/archive/epel/7/$basearch|g' /etc/yum.repos.d/epel.repo
RUN sed -i 's|baseurl=http://download.fedoraproject.org/pub/epel/7/$basearch/debug|baseurl=https://archives.fedoraproject.org/pub/archive/epel/7/$basearch/debug|g' /etc/yum.repos.d/epel.repo
RUN sed -i 's|baseurl=http://download.fedoraproject.org/pub/epel/7/SRPMS|baseurl=https://archives.fedoraproject.org/pub/archive/epel/7/SRPMS|g' /etc/yum.repos.d/epel.repo

RUN yum -y install \
    centos-release-scl-rh

# Special handling for CentOS-SCLo-rh.repo
RUN sed -i s/mirror.centos.org/vault.centos.org/g /etc/yum.repos.d/CentOS-SCLo-scl-rh.repo
RUN sed -i s/^#.*baseurl=http/baseurl=http/g /etc/yum.repos.d/CentOS-SCLo-scl-rh.repo
RUN sed -i s/^mirrorlist=http/#mirrorlist=http/g /etc/yum.repos.d/CentOS-SCLo-scl-rh.repo

RUN yum -y install \
    bison \
    curl \
    dpkg \
    enchant \
    gcc \
    gcc-c++ \
    git \
    gmp-devel \
    krb5-devel \
    make \
    openldap-devel \
    postfix \
    rrdtool-devel \
    strace \
    sudo \
    vim \
    which \
    && yum clean all

RUN yum -y makecache \
    && yum -y install \
    autoconf \
    automake \
    bind-utils \
    bzip2-devel \
    curl \
    curl-devel \
    expat-devel \
    flex \
    flex-devel \
    freeradius-devel \
    gcc \
    gcc-c++ \
    gd-devel \
    gettext \
    groff \
    gtk-doc \
    httpd-devel \
    joe \
    libXpm-devel \
    libevent-devel \
    libffi-devel \
    libgsf-devel \
    libjpeg-devel \
    libmcrypt-devel \
    libpcap-devel \
    libtool \
    libtool-ltdl \
    libtool-ltdl-devel \
    libuuid-devel \
    libxml2-devel \
    libxmlsec1-devel \
    mariadb-devel \
    mpfr-devel \
    ncurses-devel \
    openssh-clients \
    openssl-devel \
    pango-devel \
    patch \
    pcre-devel \
    perl-ExtUtils-Embed \
    perl-IO-Zlib \
    perl-Locale-Maketext-Simple \
    perl-Time-HiRes \
    perl-devel \
    perl-IPC-Cmd \
    perl-Test-Simple \
    php \
    ping \
    postgresql-devel \
    readline-devel \
    rpcbind \
    rpm-build \
    rsync \
    samba-client \
    sqlite-devel \
    texinfo \
    tk-devel \
    vim \
    wget \
    which \
    xmlsec1-devel \
    xmlsec1-openssl-devel \
    && yum clean all

# Install our standard tool chain for building in seperate container
# - gnu-toolchain is needed for compiling all the C++ stuff
# - cmake is needed for e.g. building re2
# - openssl is needed by Python 3.7+
# - python is needed by our build / test chain
FROM base AS builder
ARG NEXUS_ARCHIVES_URL
ARG NEXUS_USERNAME
ARG NEXUS_PASSWORD
ARG DISTRO
ARG BRANCH_VERSION
ENV NEXUS_ARCHIVES_URL="$NEXUS_ARCHIVES_URL" NEXUS_USERNAME="$NEXUS_USERNAME" NEXUS_PASSWORD="$NEXUS_PASSWORD" DISTRO="$DISTRO" BRANCH_VERSION="$BRANCH_VERSION"

COPY scripts/* /opt/
RUN /opt/install-gnu-toolchain.sh
RUN /opt/install-valgrind.sh
RUN /opt/install-cmake.sh
RUN /opt/install-protobuf-cpp.sh
RUN /opt/install-openssl.sh
RUN /opt/install-python.sh
RUN /opt/install-freetds.sh
RUN /opt/install-rust-cargo.sh

# Now shrink all the binaries and libraries we produced to build a small image
# in the next step
RUN /opt/strip_binaries /opt

# Run this AFTER strip_binaries!!
RUN /opt/install-bazel.sh

### Actual Image ###
FROM base

# Copy our standard tool chain for building
COPY --from=builder /opt /opt
ARG DISTRO
ARG BRANCH_VERSION
ENV DISTRO="$DISTRO" BRANCH_VERSION="$BRANCH_VERSION"

# Set symlinks
RUN /opt/install-gnu-toolchain.sh link-only
RUN /opt/install-valgrind.sh link-only
RUN /opt/install-cmake.sh link-only
RUN /opt/install-protobuf-cpp.sh --link-only
RUN /opt/install-python.sh link-only
RUN /opt/install-freetds.sh link-only
RUN /opt/install-bazel.sh link-only
RUN /opt/install-rust-cargo.sh link-only

# Install non cached dependencies
RUN /opt/install-pipenv.sh
RUN /opt/install-cmk-dependencies.sh
RUN /opt/install-patchelf.sh

# The /etc/fstab does not exist in the base image we use. A missing fstab prevents OMD from
# using a tmpfs for /omd/sites/[site]/tmp, which we want to have during our tests. We can
# simply solve this by pre-creating the empty file here.
RUN touch /etc/fstab

# Ensure all our build containers have the jenkins user (with same uid/gid). The non privileged
# jobs will be executed as this user in the container
RUN groupadd -g 1000 jenkins \
    && useradd -m -u 1001 -g 1000 -s /bin/bash jenkins

RUN mkdir -p /home/jenkins/.cache/ \
    && chown jenkins:jenkins /home/jenkins/.cache/

ARG VERS_TAG
RUN echo $VERS_TAG > /version.txt

ENV RUSTUP_HOME=/opt/rust/rustup
LABEL \
    com.checkmk.image_type="build-image"
