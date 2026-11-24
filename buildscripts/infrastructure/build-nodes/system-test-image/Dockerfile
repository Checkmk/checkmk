# The environment of the image the system test shards of the medium chain run
# in, one per run: the checkout at /git and its .venv, owned by testuser. No
# package: package.Dockerfile builds on this image and installs the package
# the medium chain pre-built. Split so the medium chain builds this part while
# the package is being built, and only the package installation waits for it.
# See single_tests.run_make_target_k8s() for how the shards use the result.
#
# Built by build-build-image.groovy ("mc-system-tests-env", pushed as
# mc-system-tests:<run>-env). Its context is not the checkout directory but
# this layout:
#   git/                     the files git tracks and .git (tests/testlib runs
#                            git commands)
#   venv-build/remote.bazelrc
#                            the remote cache, for the venv stage only
# Nothing untracked in git/, so no credentials and no .venv.
#
# Local test, with such a context in /tmp/ctx-env:
#
# docker build \
#   --build-arg IMAGE_BASE='artifacts.lan.tribe29.com:4000/ubuntu-24.04:master-latest' \
#   --tag mc-system-tests:local-test-env \
#   -f buildscripts/infrastructure/build-nodes/system-test-image/Dockerfile \
#   /tmp/ctx-env

ARG IMAGE_BASE

FROM ${IMAGE_BASE} AS venv

# No Bazel server: kaniko waits for every process a RUN leaves behind, and the
# server cannot be shut down in here (bazel shutdown hangs, exit 36). A
# startup option in the system rc file, the repository's .bazelrc stays as is.
RUN echo "startup --batch" >> /etc/bazel.bazelrc

COPY git/ /git/
WORKDIR /git

# Bazel starts without any cache in here, the remote cache saves it from
# building everything anew. It holds the credentials of the remote cache:
# only in this stage, which is not part of the image, its layers are not
# pushed.
COPY venv-build/remote.bazelrc /git/remote.bazelrc

# Where bazelisk downloads Bazel from: the mirror the CI pods use, instead of
# the default of .bazeliskrc. Left out (empty), .bazeliskrc applies.
ARG BAZELISK_BASE_URL

# Only the venv and its interpreter leave this stage, not Bazel's caches or
# remote.bazelrc.
RUN if [ -z "${BAZELISK_BASE_URL}" ]; then unset BAZELISK_BASE_URL; fi \
    && buildscripts/infrastructure/build-nodes/system-test-image/stage-venv.sh /stage

FROM ${IMAGE_BASE}

# The user the system tests run as. Here and not when the container starts, so
# a shard does not first have to chown the whole checkout to it.
RUN useradd --create-home --shell /bin/bash testuser \
    && echo "testuser ALL=(ALL) NOPASSWD: ALL" > /etc/sudoers.d/testuser \
    && chmod 0440 /etc/sudoers.d/testuser

COPY --from=venv /stage/opt/ /opt/
COPY --from=venv --chown=testuser:testuser /stage/git/ /git/
COPY --chown=testuser:testuser git/ /git/
WORKDIR /git
