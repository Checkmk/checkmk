#!/usr/bin/env bash

# Return SHA of image referenced by $1
# echo "$(grep $1 $SCRIPT_DIR/docker_image_aliases.txt | awk '{print $2}')"
#

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" >/dev/null 2>&1 && pwd)"

RESOLVE_ERROR_FILE="docker-image-alias-resolve-error.txt"

DOCKER_RESULT=$(docker build "${SCRIPT_DIR}/$1" 2>${RESOLVE_ERROR_FILE})
RESULT_IMAGE_ID=$(awk '/Successfully built/{print $3}' <<<"${DOCKER_RESULT}")

if [ -n "$RESULT_IMAGE_ID" ]; then
    echo "$RESULT_IMAGE_ID"
else
    echo "Could not resolve $1, error was:" 1>&2
    cat ${RESOLVE_ERROR_FILE} 1>&2
    echo "Make sure the image alias exists, you're correctly logged into the registry and the image exists on the registry" 1>&2
    echo "INVALID_IMAGE_ID"
    # shellcheck disable=SC2242 # Can only exit with status 0-255
    exit -1
fi

rm -f ${RESOLVE_ERROR_FILE}

# >>> This is a workaround for images being deleted on Nexus.
#     It should be replaced with a solution which allows to keep images forever without having
#     to pull them regularly.

# Get the nexus repo tag via the meta.yml file. You're asking why not via docker image inspect?
# It seems that we don't always get the nexus repo tag via the field "RepoTags", so we go this way...
REPO_TAG=$(grep "tag:" "${SCRIPT_DIR}/$1/meta.yml" | awk '{ print $2}')

if [ -z "$REPO_TAG" ]; then
    exit
fi

# We need to pull also the tag, otherwise Nexus may delete those images
docker pull --quiet "${REPO_TAG}" >/dev/null || true

# <<<
