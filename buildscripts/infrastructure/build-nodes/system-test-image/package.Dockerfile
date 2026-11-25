# The image the system test shards of the medium chain run in, one per run:
# the environment image of the run (see Dockerfile: the checkout at /git and
# its .venv) with the Checkmk package the medium chain pre-built, installed.
# The shards start their tests right away instead of each setting all of that
# up, see single_tests.run_make_target_k8s().
#
# Built by build-build-image.groovy ("mc-system-tests", pushed as
# mc-system-tests:<run>) once the package and the environment image of the
# run are there. Its context is empty.
#
# The package is not copied in, it only has to be there for the installation:
# PACKAGE_DIR is a directory on the workspace volume of the kaniko container.
# kaniko leaves mounted volumes out of its snapshots, so nothing of it gets
# into the image. kaniko has no RUN --mount.
#
# Local test, the same way, with the package in ~/kaniko-pkg/package_download,
# this file in ~/kaniko-pkg and an empty ~/kaniko-pkg/ctx (docker may not see
# /tmp):
#
# docker run --rm \
#   -v ~/kaniko-pkg:/home/jenkins/agent \
#   -v ~/.docker/config.json:/kaniko/.docker/config.json:ro \
#   martizih/kaniko:v1.27.6-alpine \
#   --context /home/jenkins/agent/ctx \
#   --dockerfile /home/jenkins/agent/package.Dockerfile \
#   --build-arg ENV_IMAGE=artifacts.lan.tribe29.com:4000/mc-system-tests:<run>-env \
#   --build-arg PACKAGE_DIR=/home/jenkins/agent/package_download \
#   --build-arg EDITION=ultimate \
#   --build-arg VERSION=2.6.0-2026.11.19 \
#   --build-arg BRANCH=master \
#   --no-push --tar-path /home/jenkins/agent/image.tar \
#   --destination mc-system-tests:local-test

ARG ENV_IMAGE

FROM ${ENV_IMAGE}

ARG EDITION
ARG VERSION
ARG BRANCH
ENV EDITION=${EDITION} VERSION=${VERSION} BRANCH=${BRANCH}

ARG PACKAGE_DIR

# install-cmk.py installs the package from package_download/ (see
# tests/testlib/system/package_manager.py), as a shard would. Without a package
# there it would fall back to another one, hence the check. The link goes in
# the same step, so it is not in the image either.
# SKIP_MAKEFILE_CALL: run-uvenv would otherwise run `make .venv` again.
# Installing needs root. Whatever that leaves in /git goes to testuser, only
# those files, so the layer does not copy the whole checkout again.
RUN if ! ls "${PACKAGE_DIR}"/check-mk-*.deb >/dev/null 2>&1; then \
        echo "No check-mk-*.deb in PACKAGE_DIR '${PACKAGE_DIR}'" >&2; exit 1; \
    fi \
    && ln -s "${PACKAGE_DIR}" /git/package_download \
    && su testuser -s /bin/sh -c '/git/.venv/bin/python -c "import ssl, sqlite3"' \
    && SKIP_MAKEFILE_CALL=1 scripts/run-uvenv tests/scripts/install-cmk.py \
    && rm /git/package_download \
    && find /git ! -user testuser -exec chown --no-dereference testuser:testuser {} + \
    && ls /omd/versions/default

LABEL com.checkmk.image_type="system-test-image"
