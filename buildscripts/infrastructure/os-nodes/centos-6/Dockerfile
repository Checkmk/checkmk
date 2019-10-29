FROM centos:6

# Use a login shell to make the definitions from /etc/profile.d/enable-python27.sh
# available to the "RUN" commands below
SHELL ["/bin/bash", "-l", "-c"]

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
# (https://access.redhat.com/solutions/527703)
RUN echo -e "source scl_source enable python27" > /etc/profile.d/enable-python27.sh

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

ARG VERS_TAG
RUN echo $VERS_TAG > /version.txt
