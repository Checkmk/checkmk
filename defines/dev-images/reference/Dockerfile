ARG BASE_BUILD_IMAGE

FROM ${BASE_BUILD_IMAGE}

ENV \
    DEBIAN_FRONTEND=noninteractive \
    LC_ALL=C.UTF-8 \
    LANG=C.UTF-8

# needed because of later installs and apt-cache get's purged
RUN apt-get update

# golang-go: needed for install-buildifier.sh
# msitools:  needed for `msiinfo` in test source package
# libenchant1c2a:  needed for building the software architecture as we're using sphinxcontrib.spelling

# Those are still unclear:
#   php7.4-common
#   default-jdk
#   upx-ucl
#   dpatch

RUN apt-get install -y \
    golang-go \
    msitools \
    libenchant1c2a

# Despite files needed for builds might already be available in build images
# copy them again, in case they changed
COPY \
    .bazelversion \
    package_versions.bzl \
    static_variables.bzl \
    defines.make \
    /opt/

COPY --from=scripts \
    build_lib.sh \
    Check_MK-pubkey.gpg \
    /opt/

COPY --from=scripts install-docker.sh /opt/
RUN /opt/install-docker.sh

COPY --from=scripts install-make-dist-deps.sh /opt/
RUN /opt/install-make-dist-deps.sh

COPY --from=scripts install-nodejs.sh /opt/
RUN /opt/install-nodejs.sh

COPY --from=scripts install-iwyu.sh install-clang.sh /opt/
RUN /opt/install-clang.sh

COPY --from=scripts install-shellcheck.sh /opt/
RUN /opt/install-shellcheck.sh

COPY --from=scripts install-musl-tools.sh /opt/
RUN /opt/install-musl-tools.sh

COPY --from=scripts install-packer.sh /opt/
RUN /opt/install-packer.sh

COPY --from=scripts install-aws-cli.sh /opt/
RUN /opt/install-aws-cli.sh

COPY --from=scripts install-buildifier.sh /opt/
RUN /opt/install-buildifier.sh

