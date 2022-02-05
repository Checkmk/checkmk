ARG IMAGE_DEBIAN_11
# hadolint ignore=DL3006
FROM ${IMAGE_DEBIAN_11}

SHELL ["/bin/bash", "-c"]
ENV DEBIAN_FRONTEND=noninteractive LC_ALL=C.UTF-8 LANG=C.UTF-8 PATH="/opt/bin:${PATH}"

#    libenchant1c2a \

RUN apt-get update \
    && apt-get install -y \
    default-libmysqlclient-dev \
    gdebi \
    git \
    libkrb5-dev \
    libldap2-dev \
    librrd-dev \
    libsasl2-dev \
    libssl-dev \
    make \
    python-dev \
    python-dev \
    python3-pip \
    rrdtool \
    strace \
    sudo \
    vim \
    && rm -rf /var/lib/apt/lists/*

RUN apt-get update \
    && apt-get install -y \
    apache2 \
    apache2-dev \
    build-essential \
    curl \
    default-libmysqlclient-dev \
    dietlibc-dev \
    dnsutils \
    dpatch \
    flex \
    gettext \
    git-buildpackage \
    gtk-doc-tools \
    iputils-ping \
    joe \
    libcurl4-openssl-dev \
    libdbi-dev \
    libevent-dev \
    libffi-dev \
    libfreeradius-dev \
    libgd-dev \
    libglib2.0-dev \
    libgnutls28-dev \
    libgsf-1-dev \
    libkrb5-dev \
    libldap2-dev \
    libltdl-dev \
    libmcrypt-dev \
    libncurses5-dev \
    libpango1.0-dev \
    libpcap-dev \
    libperl-dev \
    libpq-dev \
    libreadline-dev \
    libsqlite3-dev \
    libssl-dev \
    libxml2-dev \
    libxmlsec1-dev \
    openssh-client \
    patch \
    rpcbind \
    rsync \
    smbclient \
    texinfo \
    tk-dev \
    uuid-dev \
    vim \
    libc6-dbg \
    && rm -rf /var/lib/apt/lists/*

# Install our standard tool chain for building
# - gnu-toolchain is needed for compiling all the C++ stuff
# - cmake is needed for e.g. building re2
# - openssl is needed by Python 3.7+
# - python is needed by our build / test chain
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
RUN /opt/install-pipenv.sh
RUN /opt/install-freetds.sh
RUN /opt/install-rust-cargo.sh
RUN /opt/install-cmk-dependencies.sh
RUN /opt/install-patchelf.sh

# Ensure all our build containers have the jenkins user (with same uid/gid). The non privileged
# jobs will be executed as this user in the container
RUN groupadd -g 1000 jenkins \
    && useradd -m -u 1001 -g 1000 -s /bin/bash jenkins

ARG VERS_TAG
RUN echo $VERS_TAG > /version.txt

LABEL \
    com.tribe29.image_type="build-image"
