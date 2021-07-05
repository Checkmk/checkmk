#!/usr/bin/env bash
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" >/dev/null 2>&1 && pwd)"

cd $SCRIPT_DIR

docker build $1 | awk '/Successfully built/{print $3}'

# echo "$(grep $1 $SCRIPT_DIR/docker_image_aliases.txt | awk '{print $2}')"
