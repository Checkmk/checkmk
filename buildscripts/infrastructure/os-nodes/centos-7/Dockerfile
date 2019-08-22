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
RUN curl https://bootstrap.pypa.io/get-pip.py -o get-pip.py \
    && scl enable python27 'python get-pip.py'
RUN scl enable python27 'pip install --upgrade setuptools virtualenv' \
    && scl enable python27 'pip install git+https://github.com/svenpanne/pipenv.git@41f30d7ac848fdfe3eb548ddd19b731bfa8c331a'
RUN yum -y install \
    $PACKAGES \
    && yum clean all

# Set Environment Variables to activate python27
ENV PATH=/opt/rh/python27/root/usr/bin${PATH:+:${PATH}}
ENV LD_LIBRARY_PATH=/opt/rh/python27/root/usr/lib64${LD_LIBRARY_PATH:+:${LD_LIBRARY_PATH}}
ENV MANPATH=/opt/rh/python27/root/usr/share/man:${MANPATH}
ENV XDG_DATA_DIRS=/opt/rh/python27/root/usr/share:${XDG_DATA_DIRS:-/usr/local/share:/usr/share}
ENV PKG_CONFIG_PATH=/opt/rh/python27/root/usr/lib64/pkgconfig${PKG_CONFIG_PATH:+:${PKG_CONFIG_PATH}}
