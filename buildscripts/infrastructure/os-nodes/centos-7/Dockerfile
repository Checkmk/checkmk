FROM centos:7

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
    dpkg \
    enchant \
    gcc \
    gcc-c++ \
    git \
    krb5-devel \
    make \
    mysql-devel \
    nodejs \
    npm \
    openldap-devel \
    postfix \
    python27 \
    python27-devel \
    rrdtool-devel \
    strace \
    sudo \
    vim \
    which

# CentOS 7 has 2.7.5 installed by default. The pipenv we need does not work with
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
    && pip install git+https://github.com/svenpanne/pipenv.git@41f30d7ac848fdfe3eb548ddd19b731bfa8c331a

RUN yum -y install \
    $PACKAGES \
    && yum clean all

# The /etc/fstab does not exist in the base image we use. A missing fstab prevents OMD from
# using a tmpfs for /omd/sites/[site]/tmp, which we want to have during our tests. We can
# simply solve this by pre-creating the empty file here.
RUN touch /etc/fstab
