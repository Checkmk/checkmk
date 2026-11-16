# The image the system test shards of the medium chain run in, one per run:
# the checkout at /git, its .venv and the Checkmk package the medium chain
# pre-built, installed. The shards start their tests right away instead of
# each setting all of that up, see single_tests.run_make_target_k8s().
#
# Built by build-build-image.groovy ("mc-system-tests"). Its context is not
# the checkout directory but this layout:
#   git/                     the files git tracks, .git (tests/testlib runs
#                            git commands) and package_download/ with the
#                            package
#   venv-build/remote.bazelrc
#                            the remote cache, for the venv stage only
# Nothing untracked in git/, so no credentials and no .venv.
#
# Local test, with such a context in /tmp/ctx:
#
# docker build \
#   --build-arg IMAGE_BASE='artifacts.lan.tribe29.com:4000/ubuntu-24.04:master-latest' \
#   --build-arg EDITION=ultimate \
#   --build-arg VERSION=2.6.0-2026.11.19 \
#   --build-arg BRANCH=master \
#   --tag mc-system-tests:local-test \
#   -f buildscripts/infrastructure/build-nodes/system-test-image/Dockerfile \
#   /tmp/ctx

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

ARG EDITION
ARG VERSION
ARG BRANCH
ENV EDITION=${EDITION} VERSION=${VERSION} BRANCH=${BRANCH}

# install-cmk.py installs the package from package_download/ (see
# tests/testlib/system/package_manager.py), as a shard would.
# SKIP_MAKEFILE_CALL: run-uvenv would otherwise run `make .venv` again.
# Installing needs root. Whatever that leaves in /git goes to testuser, only
# those files, so the layer does not copy the whole checkout again.
RUN su testuser -s /bin/sh -c '/git/.venv/bin/python -c "import ssl, sqlite3"' \
    && SKIP_MAKEFILE_CALL=1 scripts/run-uvenv tests/scripts/install-cmk.py \
    && find /git ! -user testuser -exec chown --no-dereference testuser:testuser {} + \
    && ls /omd/versions/default

LABEL com.checkmk.image_type="system-test-image"
