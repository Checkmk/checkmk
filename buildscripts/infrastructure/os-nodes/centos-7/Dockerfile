FROM centos:7

SHELL ["/bin/bash", "-c"]

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

RUN yum -y install \
    $PACKAGES \
    && yum clean all

# The /etc/fstab does not exist in the base image we use. A missing fstab prevents OMD from
# using a tmpfs for /omd/sites/[site]/tmp, which we want to have during our tests. We can
# simply solve this by pre-creating the empty file here.
RUN touch /etc/fstab

# New packages that are not needed for the build toolchain above should be added here.
# We avoid rebuild of the whole previous steps this way
RUN yum -y makecache \
    && yum -y install \
    joe \
    vim \
    && yum clean all

ARG VERS_TAG
RUN echo $VERS_TAG > /version.txt
