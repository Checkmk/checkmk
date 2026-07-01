ARG DISTRO_IMAGE_BASE

# hadolint ignore=DL3006
# Create base image
FROM ${DISTRO_IMAGE_BASE} AS base

SHELL ["/bin/bash", "-c"]
ENV \
    DEBIAN_FRONTEND=noninteractive \
    LC_ALL=C.UTF-8 \
    LANG=C.UTF-8 \
    PATH="/opt/bin:${PATH}"

# Fix for CMK-23806, using our internal apt mirror
RUN sed -i "s|http://.*.ubuntu.com/ubuntu|http://apt.lan.checkmk.net/ubuntu|g" /etc/apt/sources.list

RUN apt-get update

RUN apt-get install -y \
    dialog \
    git \
    graphviz \
    libsasl2-dev \
    libxml2 \
    make \
    nullmailer \
    php-common \
    python3-dev \
    python3-pip \
    strace \
    sudo \
    vim

RUN apt-get install -y --fix-missing \
    apache2 \
    apache2-dev \
    autoconf \
    build-essential \
    bison \
    curl \
    devscripts \
    dnsutils \
    dpatch \
    flex \
    gawk \
    gettext \
    git-buildpackage \
    gtk-doc-tools \
    iproute2 \
    iputils-ping \
    joe \
    jq \
    libc6-dbg \
    libcurl4-openssl-dev \
    libevent-dev \
    libffi-dev \
    libfreeradius-dev \
    libgd-dev \
    libglib2.0-dev \
    libgmp-dev \
    libgnutls28-dev \
    libgsf-1-dev \
    libkrb5-dev \
    libldap2-dev \
    libltdl-dev \
    libmcrypt-dev \
    libmysqlclient-dev \
    libncurses5-dev \
    libpango1.0-dev \
    libpcap-dev \
    libperl-dev \
    libpq-dev \
    libreadline-dev \
    libsqlite3-dev \
    libssl-dev \
    libtool \
    libxml2-dev \
    libxmlsec1-dev \
    libmpfr-dev \
    netcat-openbsd \
    openssh-client \
    patch \
    rpcbind \
    rsync \
    smbclient \
    software-properties-common \
    texinfo \
    tk-dev \
    uuid-dev

# remove apt service because we don't need it and we run into problems, see
# https://jira.lan.tribe29.com/browse/CMK-16607
RUN rm /etc/cron.daily/apt-compat

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
COPY \
    .bazelversion \
    package_versions.bzl \
    defines.make \
    /opt/

COPY \
    build_lib.sh \
    Check_MK-pubkey.gpg \
    /opt/

COPY install-gnu-toolchain.sh /opt/
RUN /opt/install-gnu-toolchain.sh

COPY install-valgrind.sh /opt/
RUN /opt/install-valgrind.sh

COPY install-cmake.sh /opt/
RUN /opt/install-cmake.sh

COPY install-protobuf-cpp.sh /opt/
RUN /opt/install-protobuf-cpp.sh

COPY install-openssl.sh /opt/
RUN /opt/install-openssl.sh

COPY install-python.sh /opt/
RUN /opt/install-python.sh

# install GDB after Python as it requires shared object files, see CMK-15854
COPY install-gdb.sh /opt/
RUN /opt/install-gdb.sh

# Now shrink all the binaries and libraries we produced to build a small image
# in the next step
COPY strip_binaries /opt/
RUN /opt/strip_binaries /opt

# Run this AFTER strip_binaries!!
COPY install-bazel.sh /opt/
RUN /opt/install-bazel.sh

### Actual Build Image ###
FROM base

# Copy our standard tool chain for building
COPY --from=builder /opt /opt

ARG DISTRO
ARG DISTRO_MK_FILE
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
RUN /opt/install-bazel.sh link-only

# Install non cached dependencies
COPY "${DISTRO_MK_FILE}" /opt/
COPY install-cmk-dependencies.sh /opt/
RUN /opt/install-cmk-dependencies.sh

COPY install-patchelf.sh /opt/
RUN /opt/install-patchelf.sh

COPY ci.bazelrc /etc/
RUN <<EOF cat >> /etc/ci.bazelrc
common:ci --@cmk//distro="ubuntu-22.04"
common:ci --action_env=DISTRO=${DISTRO}
# We encountered false cache hits with remote caching due to environment variables
# not being propagated to external dependeny builds
# In that case "--host_action_env=..." (in addition to "--action_env") might help
# Currently we don't use any external dependencies though.
common:ci --host_action_env=DISTRO=${DISTRO}
EOF

ARG VERS_TAG
RUN echo "${VERS_TAG}" > /version.txt

LABEL \
    com.checkmk.image_type="build-image"

COPY entrypoint.sh /opt/
ENTRYPOINT ["/opt/entrypoint.sh"]
