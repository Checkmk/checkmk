# The image the system test shards of the medium chain run in, one per run:
# the environment image of the run (see Dockerfile: the checkout at /git and
# its .venv) with the Checkmk package the medium chain pre-built, installed.
# The shards start their tests right away instead of each setting all of that
# up, see single_tests.run_make_target_k8s().
#
# Built by build-build-image.groovy ("mc-system-tests", pushed as
# mc-system-tests:<run>) once the package and the environment image of the
# run are there. Its context holds only the package:
#   package_download/        the package, as single_tests.fetch_package()
#                            downloads it
#
# Local test, on top of an environment image built as described in
# Dockerfile, with such a context in /tmp/ctx-package:
#
# docker build \
#   --build-arg ENV_IMAGE=mc-system-tests:local-test-env \
#   --build-arg EDITION=ultimate \
#   --build-arg VERSION=2.6.0-2026.11.19 \
#   --build-arg BRANCH=master \
#   --tag mc-system-tests:local-test \
#   -f buildscripts/infrastructure/build-nodes/system-test-image/package.Dockerfile \
#   /tmp/ctx-package

ARG ENV_IMAGE

FROM ${ENV_IMAGE}

COPY --chown=testuser:testuser package_download/ /git/package_download/

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
