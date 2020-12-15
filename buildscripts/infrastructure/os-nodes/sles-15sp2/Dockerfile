FROM registry.suse.com/suse/sle15:15.2

SHELL ["/bin/bash", "-c"]

ARG ARTIFACT_STORAGE
ARG PACKAGES

RUN zypper addrepo -G ${ARTIFACT_STORAGE}/repository/sles15sp2 sles15sp2 \
    && zypper -n --no-gpg-checks in --replacefiles \
    gawk \
    && zypper -n --no-gpg-checks in --replacefiles --force-resolution \
    curl \
    cyrus-sasl-devel \
    enchant-devel \
    gcc-c++ \
    git \
    krb5-devel \
    libmysqlclient-devel \
    make \
    nodejs10 \
    npm10 \
    openldap2-devel \
    python \
    python-devel \
    python-pyOpenSSL \
    python-xml \
    rrdtool-devel \
    sudo \
    && zypper clean -a
RUN curl https://bootstrap.pypa.io/get-pip.py -o get-pip.py \
    && python get-pip.py
RUN pip install --upgrade setuptools \
    && pip install git+https://github.com/pypa/pipenv.git@2549656dc09e132d8ba2fa6327c939f5f9a951b7 \
    && zypper -n --no-gpg-checks in --replacefiles \
    $PACKAGES \
    && zypper clean -a

# New packages that are not needed for the build toolchain above should be added here.
# We avoid rebuild of the whole previous steps this way
RUN zypper ref \
    && zypper -n in -y --force-resolution \
    joe \
    iputils \
    vim \
    && zypper clean -a

# The /etc/fstab does not exist in the base image we use. A missing fstab prevents OMD from
# using a tmpfs for /omd/sites/[site]/tmp, which we want to have during our tests. We can
# simply solve this by pre-creating the empty file here.
RUN touch /etc/fstab

ARG VERS_TAG
RUN echo $VERS_TAG > /version.txt
