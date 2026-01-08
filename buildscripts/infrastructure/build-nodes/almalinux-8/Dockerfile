ARG DISTRO_IMAGE_BASE

# hadolint ignore=DL3006
# Create base image
FROM ${DISTRO_IMAGE_BASE} AS base

SHELL ["/bin/bash", "-c"]
ENV \
    LC_ALL=C.UTF-8 \
    LANG=C.UTF-8 \
    PATH="/opt/bin:${PATH}"

RUN yum -y --enablerepo=powertools makecache && yum repolist --enablerepo=powertools \
    && yum -y --allowerasing --enablerepo=powertools install \
    bison \
    enchant \
    gcc \
    gcc-c++ \
    git \
    graphviz-gd \
    krb5-devel \
    make \
    openldap-devel \
    postfix \
    strace \
    sudo \
    vim \
    which \
    && yum clean all

RUN yum -y makecache \
    && yum -y --enablerepo=powertools install \
    bind-utils \
    curl-devel \
    expat-devel \
    flex \
    flex-devel \
    freeradius-devel \
    gd-devel \
    gettext \
    gtk-doc \
    httpd-devel \
    iproute \
    kernel-headers \
    libXpm-devel \
    libevent-devel \
    libffi-devel \
    libgsf-devel \
    libiscsi-devel \
    libjpeg-devel \
    libmpc-devel \
    libpcap-devel \
    libstdc++-devel \
    libstdc++-static \
    libtool \
    libtool-ltdl \
    libtool-ltdl-devel \
    libuuid-devel \
    libxml2-devel \
    mariadb-devel \
    mpfr-devel \
    nc \
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
    perl-Time-Piece \
    perl-devel \
    php \
    postgresql-devel \
    procps \
    readline-devel \
    rpcbind \
    rpm-build \
    rsync \
    samba-client \
    sqlite-devel \
    texinfo \
    tk-devel \
    wget \
    xmlsec1-devel \
    xmlsec1-openssl-devel \
    && yum clean all

# --nogpgcheck: Workaround for failing installation, not locally reproducable

RUN yum -y makecache \
    && yum -y --enablerepo=powertools reinstall \
    kernel-headers \
    --nogpgcheck \
    && yum clean all

# epel release is needed for joe
# --nogpgcheck: Workaround for failing installation, not locally reproducable
RUN yum -y makecache \
    && yum -y install \
    epel-release \
    --nogpgcheck \
    && yum clean all

# New packages that are not needed for the build toolchain above should be added here.
# We avoid rebuild of the whole previous steps this way
# --nogpgcheck: Workaround for failing installation, not locally reproducable
RUN yum -y makecache \
    && yum -y --enablerepo=powertools install \
    joe \
    iputils \
    jq \
    vim \
    --nogpgcheck \
    && yum clean all

# Avoid the annobin chaos on CentOS 8, part 2:
# See also: omd/omd.spec.in
RUN if test -f /usr/lib/rpm/redhat/redhat-annobin-cc1; then \
    rm -f /usr/lib/rpm/redhat/redhat-annobin-cc1 \
    && touch /usr/lib/rpm/redhat/redhat-annobin-cc1; \
    fi

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

# The /etc/fstab does not exist in the base image we use. A missing fstab prevents OMD from
# using a tmpfs for /omd/sites/[site]/tmp, which we want to have during our tests. We can
# simply solve this by pre-creating the empty file here.
RUN touch /etc/fstab

COPY ci.bazelrc /etc/
RUN <<EOF cat >> /etc/ci.bazelrc
common:ci --@cmk//distro="almalinux-8"
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
