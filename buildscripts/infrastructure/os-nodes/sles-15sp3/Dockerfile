#Use same pinned image as 2.0.0 branch uses to be in sync with mirror
#FROM registry.suse.com/suse/sle15:15.3
FROM artifacts.lan.tribe29.com:4000/sle15@sha256:64284bcccbda0781a4986348fd41d2f44c925848a8c8cdf82eb9fb0dde3db1cb

SHELL ["/bin/bash", "-c"]

ARG ARTIFACT_STORAGE
ARG PACKAGES

RUN zypper addrepo -G ${ARTIFACT_STORAGE}/repository/sles15sp3 sles15sp3 \
    && zypper ref -s \
    && zypper -n --no-gpg-checks in --replacefiles \
    gawk \
    && zypper -n --no-gpg-checks in --replacefiles --force-resolution \
    curl \
    cyrus-sasl-devel \
    enchant-devel \
    gcc-c++ \
    git \
    krb5-devel \
    make \
    nodejs14 \
    npm14 \
    openldap2-devel \
    postfix \
    python \
    python-devel \
    python-xml \
    rrdtool-devel \
    sudo \
    && zypper clean -a
RUN curl https://bootstrap.pypa.io/pip/2.7/get-pip.py -o get-pip.py \
    && python get-pip.py
RUN pip install --upgrade setuptools \
    && pip install git+https://github.com/pypa/pipenv.git@v2020.6.2 \
    && zypper -n --no-gpg-checks in --replacefiles --force-resolution \
    $PACKAGES \
    && zypper clean -a

# New packages that are not needed for the build toolchain above should be added here.
# We avoid rebuild of the whole previous steps this way
RUN zypper -n in -y --force-resolution \
    iputils \
    vim \
    && zypper clean -a

# The /etc/fstab does not exist in the base image we use. A missing fstab prevents OMD from
# using a tmpfs for /omd/sites/[site]/tmp, which we want to have during our tests. We can
# simply solve this by pre-creating the empty file here.
RUN touch /etc/fstab

ARG VERS_TAG
RUN echo $VERS_TAG > /version.txt
