#!/usr/bin/env bash

# update Dockerfile-based image tags

# If you plan to migrate this script to another interpreter keep in mind it has to run on bare
# Jenkins nodes

# shellcheck disable=SC2164
cd "$(dirname "${BASH_SOURCE[0]}")"

if [ -z "$*" ]; then
    echo "Provide a list of image alias names or 'all' for all registered images"
    exit 0
fi

IMAGE_ALIASES=$([ "$1" = "all" ] && echo IMAGE_* || echo "$@")

for i in $IMAGE_ALIASES; do
    if [ ! -f "$i/meta.yml" ]; then
        echo "$i/meta.yml does not exist please provide existing image aliases only"
        # shellcheck disable=SC2242 # Can only exit with status 0-255
        exit -1
    fi
done

# Use the global .venv to have required modules available
make -C ../.. .venv
# shellcheck source=/dev/null
source ../../.venv/bin/activate

# Still test if the modules used in register.py are available before removing the folders
echo -n "Testing if required Python modules are available..."
(python3 -c "import docker; import yaml" && echo "OK") || exit 1

echo "Update images for: $IMAGE_ALIASES"

for i in $IMAGE_ALIASES; do
    echo "Update image for $i"
    CMD="./register.py $i $(awk '/source: /{print $2}' <"$i/meta.yml")"
    echo "remove old image alias $(dirname "${BASH_SOURCE[0]}")/$i"
    PWD="$(pwd)"
    rm -rf "${PWD:?}/$i"
    echo "re-register $i by running $CMD"
    $CMD
done
