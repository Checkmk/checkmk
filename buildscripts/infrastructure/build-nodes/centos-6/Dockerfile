FROM centos:6

SHELL ["/bin/bash", "-c"]
ENV PATH="/opt/bin:${PATH}"

RUN yum -y --enablerepo=extras install \
    epel-release \
    && yum -y install \
    centos-release-scl-rh \
    && yum -y install \
    curl \
    && curl http://mirror.ghettoforge.org/distributions/gf/el/6/plus/x86_64/rsync-3.1.2-1.gf.el6.x86_64.rpm --output rsync-3.1.2-1.gf.el6.x86_64.rpm \
    && rpm -i rsync-3.1.2-1.gf.el6.x86_64.rpm \
    && rm rsync-3.1.2-1.gf.el6.x86_64.rpm \
    && yum -y install \
    dpkg \
    enchant \
    gcc \
    git \
    krb5-devel \
    make \
    mysql-devel \
    openldap-devel \
    postfix \
    python27 \
    python27-devel \
    rrdtool-devel \
    strace \
    sudo \
    vim \
    which \
    && yum clean all

RUN yum -y makecache \
    && yum -y install \
    bind-utils \
    centos-release-scl \
    compat-readline5 \
    curl \
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
    chrpath \
    joe \
    ping \
    vim \
    && yum -y install devtoolset-7 \
    && yum clean all

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
RUN /opt/install-cmake.sh
RUN /opt/install-openssl.sh
RUN /opt/install-python2.sh
RUN /opt/install-python.sh
RUN /opt/install-pipenv.sh
RUN /opt/install-nodejs.sh
RUN /opt/install-freetds.sh

# The /etc/fstab does not exist in the base image we use. A missing fstab prevents OMD from
# using a tmpfs for /omd/sites/[site]/tmp, which we want to have during our tests. We can
# simply solve this by pre-creating the empty file here.
RUN touch /etc/fstab \
    && rm -f /etc/mtab \
    && cp /proc/mounts /etc/mtab

ARG VERS_TAG
RUN echo $VERS_TAG > /version.txt
