ARG BASE_BUILD_IMAGE=you_forgot_to_set:base_build_image

FROM ${BASE_BUILD_IMAGE}

ENV \
    DEBIAN_FRONTEND=noninteractive \
    LC_ALL=C.UTF-8 \
    LANG=C.UTF-8

# needed because of later installs and apt-cache get's purged
RUN apt-get update

# default-jdk: needed for validating the compiled werks (see compile-all-werks.groovy)
# libenchant1c2a:  needed for building the software architecture as we're using sphinxcontrib.spelling
# lsb-release: needed for install_docker
# msitools:  needed for `msiinfo` in test source package
# jq: for parsing json in shell unit tests
# tree: for debugging purposes (quickly get insights about eg generated or downloaded folders)

RUN apt-get install -y \
    default-jdk-headless \
    jq \
    libenchant-2-dev \
    lsb-release \
    msitools \
    wget \
    tree  \
    libaio1

# Despite files needed for builds might already be available in build images
# copy them again, in case they changed
COPY \
    .bazelversion \
    package_versions.bzl \
    defines.make \
    /opt/

COPY \
    build_lib.sh \
    Check_MK-pubkey.gpg \
    /opt/

# timing: real 1m57.766s user 4m42.879s sys 0m14.978s
COPY \
    install-iwyu.sh \
    install-clang.sh \
    /opt/
RUN /opt/install-clang.sh

# timing: real 0m27.583s user 0m15.425s sys 0m2.999s
COPY \
    install-docker.sh \
    /opt/
RUN /opt/install-docker.sh

# timing: real 0m13.629s user 0m9.842s sys 0m1.944s
COPY \
    install-nodejs.sh \
    /opt/
RUN /opt/install-nodejs.sh

# timing: real 0m9.257s user 0m5.424s sys 0m1.103s
COPY \
    install-packer.sh \
    /opt/
RUN /opt/install-packer.sh

# timing: real 0m7.677s user 0m4.898s sys 0m0.805s
COPY \
    install-make-dist-deps.sh \
    /opt/
RUN /opt/install-make-dist-deps.sh

# timing: real 0m8.192s user 0m2.279s sys 0m1.352s
COPY \
    install-aws-cli.sh \
    /opt/
RUN /opt/install-aws-cli.sh

COPY \
    entrypoint.sh \
    /opt/
