ARG IMAGE_SLES_15SP4

# hadolint ignore=DL3006
# Create base image
FROM ${IMAGE_SLES_15SP4} AS base

SHELL ["/bin/bash", "-c"]
ENV PATH="/opt/bin:${PATH}"

ARG ARTIFACT_STORAGE

RUN zypper addrepo -G ${ARTIFACT_STORAGE}/repository/sles15sp4 sles15sp4 \
    && zypper -n --no-gpg-checks in --replacefiles \
    gawk \
    && zypper -n --no-gpg-checks in --replacefiles \
    curl \
    cyrus-sasl-devel \
    enchant-devel \
    git \
    krb5-devel \
    make \
    python \
    python3-devel \
    rrdtool-devel \
    sudo \
    && zypper clean -a

RUN zypper ref -s \
    && zypper -n in -y --force-resolution \
    apache2-devel \
    bind-utils \
    bison \
    flex \
    freeradius-client-devel \
    freetype2-devel \
    gcc \
    gcc-c++ \
    gd-devel \
    groff \
    gtk-doc \
    intltool \
    iputils \
    jq \
    libXpm-devel \
    libbz2-devel \
    libcurl-devel \
    libevent-devel \
    libexpat-devel \
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
    libxslt-devel \
    libxmlsec1-1 \
    xmlsec1-devel \
    xmlsec1-openssl-devel \
    mariadb-client \
    openldap2-devel \
    openssh \
    pango-devel \
    patch \
    postgresql13-server-devel \
    readline-devel \
    rpcbind \
    rpm-build \
    rpm-devel \
    rsync \
    samba-client \
    sqlite3-devel \
    tar \
    texinfo \
    tk-devel \
    unzip \
    wget \
    vim \
    && zypper clean -a

# krb5-devel installs krb5-config which will be in $PATH when /etc/profile is sourced
# This is needed and expected by setup.py of pykerberos for properly linking against the needed libs.
# However we're executing the make targets within the container in a "non-login" shell and /etc/profile is not sourced.
# Sourcing this file during the container creation led to several other issues (no tty available etc.).
# That's why, we're going this direct way now.
ENV PATH="/usr/lib/mit/bin:${PATH}"

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
ENV \
    NEXUS_ARCHIVES_URL="${NEXUS_ARCHIVES_URL}" \
    NEXUS_USERNAME="${NEXUS_USERNAME}" \
    NEXUS_PASSWORD="${NEXUS_PASSWORD}" \
    DISTRO="${DISTRO}" \
    BRANCH_VERSION="${BRANCH_VERSION}"

# Copy over stuff that's needed by lots of scripts (has to be copied to context before)
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

### Actual Build Image ###
FROM base

# Copy our standard tool chain for building
COPY --from=builder /opt /opt
ARG DISTRO
ARG BRANCH_VERSION
ENV \
    DISTRO="${DISTRO}" \
    BRANCH_VERSION="${BRANCH_VERSION}"

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
RUN echo "${VERS_TAG}" > /version.txt

ENV RUSTUP_HOME=/opt/rust/rustup
LABEL \
    com.checkmk.image_type="build-image"
