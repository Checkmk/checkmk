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

ARG PACKAGES

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
    which

# CentOS 6 has 2.6.6 installed by default. The pipenv we need does not work with
# Python < 2.7.9. For this reason we install the 2.7.16 from centos-release-scl-rh
# which installs it's files to /opt/rh/python27.
#
# Enable the Python 2.7 installed from centos-release-scl-rh in all shells by default
# - https://access.redhat.com/solutions/527703
#
# It's not enough to write something to /etc/bashrc or similar, because the bashrc
# is not loaded in all cases. The following approach handles more cases:
#
# - https://github.com/sclorg/s2i-base-container/tree/8d9514866b4f4600638d0a07603552b21aa77707
#
# When bash is started non-interactively, to run a shell script, for example it
# looks for this variable and source the content of this file. This will enable
# the SCL for all scripts without need to do 'scl enable'.
ENV BASH_ENV=/opt/rh/python27/enable \
    ENV=/opt/rh/python27/enable \
    PROMPT_COMMAND=". /opt/rh/python27/enable"

# Now bring pip and pipenv to our standard version used in all environments.
RUN curl https://bootstrap.pypa.io/get-pip.py -o get-pip.py \
    && python get-pip.py
RUN pip install --upgrade setuptools virtualenv \
    && pip install git+https://github.com/pypa/pipenv.git@2549656dc09e132d8ba2fa6327c939f5f9a951b7

RUN curl -sL https://rpm.nodesource.com/setup_10.x | bash -
RUN yum -y install \
    nodejs \
    $PACKAGES \
    && yum clean all

# New packages that are not needed for the build toolchain above should be added here.
# We avoid rebuild of the whole previous steps this way
RUN yum -y makecache \
    && yum -y install \
    joe \
    ping \
    vim \
    && yum clean all

ARG VERS_TAG
RUN echo $VERS_TAG > /version.txt
