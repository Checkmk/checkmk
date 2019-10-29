FROM centos:centos8

SHELL ["/bin/bash", "-c"]

ARG PACKAGES

RUN yum -y --enablerepo=PowerTools --allowerasing install \
    epel-release \
    && yum -y --enablerepo=PowerTools --allowerasing install \
    curl \
    enchant \
    gcc \
    gcc-c++ \
    git \
    krb5-devel \
    make \
    mariadb \
    mysql-devel \
    nodejs \
    npm \
    openldap-devel \
    postfix \
    python2-devel \
    python27 \
    rrdtool-devel \
    strace \
    sudo \
    vim \
    which \
    && yum clean all

RUN ln -s /usr/bin/python2.7 /usr/bin/python \
    && python -V
RUN curl https://bootstrap.pypa.io/get-pip.py -o get-pip.py \
    && python get-pip.py
RUN pip install --upgrade setuptools virtualenv \
    && pip install git+https://github.com/svenpanne/pipenv.git@41f30d7ac848fdfe3eb548ddd19b731bfa8c331a
RUN yum -y --enablerepo=PowerTools install \
    $PACKAGES \
    && yum clean all
# The /etc/fstab does not exist in the base image we use. A missing fstab prevents OMD from
# using a tmpfs for /omd/sites/[site]/tmp, which we want to have during our tests. We can
# simply solve this by pre-creating the empty file here.
RUN touch /etc/fstab

# Set Environment Variables to activate python27
ENV PATH=/opt/rh/python27/root/usr/bin${PATH:+:${PATH}}
ENV LD_LIBRARY_PATH=/opt/rh/python27/root/usr/lib64${LD_LIBRARY_PATH:+:${LD_LIBRARY_PATH}}
ENV MANPATH=/opt/rh/python27/root/usr/share/man:${MANPATH}
ENV XDG_DATA_DIRS=/opt/rh/python27/root/usr/share:${XDG_DATA_DIRS:-/usr/local/share:/usr/share}
ENV PKG_CONFIG_PATH=/opt/rh/python27/root/usr/lib64/pkgconfig${PKG_CONFIG_PATH:+:${PKG_CONFIG_PATH}}
