ARG IMAGE_CENTOS_8
# hadolint ignore=DL3006
FROM ${IMAGE_CENTOS_8}

SHELL ["/bin/bash", "-c"]
ENV LC_ALL=C.UTF-8 LANG=C.UTF-8 PATH="/opt/bin:${PATH}"

# Centos-8 is EOL, therfor we switch to the vault repos
RUN sed -i 's/^mirrorlist/#mirrorlist/' /etc/yum.repos.d/* \
    && sed -i 's/^#baseurl\(.*\)mirror\(.*\)/baseurl\1vault\2/' /etc/yum.repos.d/*

RUN yum -y --enablerepo=powertools --allowerasing install \
    epel-release \
    && yum -y --enablerepo=powertools --allowerasing install \
    curl \
    enchant \
    gcc \
    gcc-c++ \
    git \
    krb5-devel \
    make \
    openldap-devel \
    postfix \
    graphviz-gd \
    rrdtool-devel \
    strace \
    sudo \
    vim \
    which \
    && yum clean all

RUN yum -y makecache \
    && yum -y --enablerepo=powertools install \
    bind-utils \
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
    gtk-doc \
    httpd-devel \
    isl-devel \
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
    xmlsec1-devel \
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
    vim \
    --nogpgcheck \
    && yum clean all

# Avoid the annobin chaos on CentOS 8, part 2:
# See also: omd/omd.spec.in
RUN if test -f /usr/lib/rpm/redhat/redhat-annobin-cc1; then \
        rm -f /usr/lib/rpm/redhat/redhat-annobin-cc1 \
        && touch /usr/lib/rpm/redhat/redhat-annobin-cc1; \
    fi

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

ARG VERS_TAG
RUN echo $VERS_TAG > /version.txt

LABEL \
    com.tribe29.image_type="build-image"
