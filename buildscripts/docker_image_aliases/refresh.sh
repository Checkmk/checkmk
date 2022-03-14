#!/usr/bin/env bash

# This is a workaround problem solving script - please don't use it only if you know what you're
# doing

# Take one image alias name (or find them all) and resolve, re-tag, push and pull all we know about
# that image alias in order to re-surrect it on our remote registry

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" >/dev/null 2>&1 && pwd)"

# in case no alias name has been provided, traverse them all
if [ -z "$1" ]; then
    for i in "${SCRIPT_DIR}/IMAGE_"*; do
        echo "$(basename "$i"):"
        "$SCRIPT_DIR/refresh.sh" "$(basename "$i")"
        echo "========================================"
    done
    exit 0
fi

# if we reach this point an image ID has been provided. Resolve it, re-tag it, push it and pull it.

ALIAS_NAME="$1"

IMAGE_ID="$("${SCRIPT_DIR}/resolve.sh" "${ALIAS_NAME}")"
echo "  resolved image id: ${IMAGE_ID}"

REPO_TAG=$(grep "tag:" "${SCRIPT_DIR}/${ALIAS_NAME}/meta.yml" | awk '{ print $2}')
if [ -n "$REPO_TAG" ]; then
    echo "  registered REPO_TAG: $REPO_TAG"
    docker tag "${IMAGE_ID}" "${REPO_TAG}"
fi

echo "  refresh tags:"
for TAG in $(docker image inspect "${IMAGE_ID}" | jq -r '.[] | (.RepoTags)' | grep "\-image\-alias\-" | cut -d\" -f2); do
    echo "    $(docker push --quiet "$TAG")"
    docker pull --quiet "$TAG" >/dev/null
done

# this code can be used to push all local image aliases
# for i in $(docker images --format "table {{.Repository}}:{{.Tag}}" | grep "\-image\-alias\-"); do
#    echo docker push $i
# done
