ARG BASE_IMAGE
# hadolint ignore=DL3006
FROM ${BASE_IMAGE}

SHELL ["/bin/bash", "-c"]
ENV DEBIAN_FRONTEND=noninteractive LC_ALL=C.UTF-8 LANG=C.UTF-8

ARG NEXUS_ARCHIVES_URL
ARG NEXUS_USERNAME
ARG NEXUS_PASSWORD
ARG DISTRO
ARG CI
ENV \
    NEXUS_ARCHIVES_URL="${NEXUS_ARCHIVES_URL}" \
    NEXUS_USERNAME="${NEXUS_USERNAME}" \
    NEXUS_PASSWORD="${NEXUS_PASSWORD}" \
    DISTRO="${DISTRO}" \
    CI="${CI}"

ARG ADDITIONAL_ARGS

# used by install scripts
COPY scripts/.bazelversion /opt/
COPY scripts/defines.make /opt/
COPY scripts/package_versions.bzl /opt/
COPY scripts/strip_binaries.sh /opt/
COPY scripts/*.mk /opt/
COPY scripts/*.sh /opt/

RUN /opt/install-development.sh --profile all ${ADDITIONAL_ARGS}

# run the installation a second time to confirm an additional run does not fail
# used by install scripts
COPY scripts/.bazelversion /opt/
COPY scripts/defines.make /opt/
COPY scripts/package_versions.bzl /opt/
COPY scripts/strip_binaries.sh /opt/
COPY scripts/*.mk /opt/
COPY scripts/*.sh /opt/
RUN rm -rf /root/.pyenv
RUN /opt/install-development.sh --profile all ${ADDITIONAL_ARGS}
