#!/bin/bash
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

set -ex
unset LANG

log() { echo "[$(date '+%F %T')] ==============================" "$@"; }
die() {
    log "$@"
    exit 1
}

clean_up() {
    log "Räume temporäres Verzeichnis $TMP_PATH weg"
    rm -rf "$TMP_PATH"
}
trap clean_up SIGTERM SIGHUP SIGINT EXIT

docker_tag() {
    # Tag images
    REGISTRY=$1
    FOLDER=$2
    TARGET_VERSION=$3
    if [[ -z "$TARGET_VERSION" ]]; then
        TARGET_VERSION="${VERSION_TAG}"
    fi

    SOURCE_TAG="checkmk/check-mk-${EDITION}:${VERSION_TAG}"

    log "Erstelle \"${VERSION}\" tag..."
    docker tag "${SOURCE_TAG}" "$REGISTRY$FOLDER/check-mk-${EDITION}:${TARGET_VERSION}"

    if [ "$SET_BRANCH_LATEST_TAG" = "yes" ]; then
        log "Erstelle \"{$BRANCH}-latest\" tag..."
        docker tag "${SOURCE_TAG}" "$REGISTRY$FOLDER/check-mk-${EDITION}:${BRANCH}-latest"
    fi

    if [ "$SET_LATEST_TAG" = "yes" ]; then
        log "Erstelle \"latest\" tag..."
        docker tag "${SOURCE_TAG}" "$REGISTRY$FOLDER/check-mk-${EDITION}:latest"
    fi
}

docker_push () {
    # Push images to a Registry
    REGISTRY=$1
    FOLDER=$2

    if [[ "$VERSION_TAG" == *"-rc"* ]]; then
        echo "${VERSION_TAG} was a release candidate, do a retagging before pushing".
        RELEASE_VERSION=$(echo -n ${VERSION_TAG} | sed 's/-rc[0-9]*//g')
        if [ $EDITION = raw ] || [ "$EDITION" = free ]; then
            docker_tag "" "checkmk" "${RELEASE_VERSION}"
        else
            docker_tag "registry.checkmk.com" "/${EDITION}" "${RELEASE_VERSION}"
        fi
    else
        RELEASE_VERSION="${VERSION_TAG}"
    fi


    log "Lade zu ($REGISTRY) hoch..."
    docker login ${REGISTRY} -u ${DOCKER_USERNAME} -p ${DOCKER_PASSPHRASE}
    DOCKERCLOUD_NAMESPACE=checkmk docker push "$REGISTRY$FOLDER/check-mk-${EDITION}:${RELEASE_VERSION}"

    if [ "$SET_BRANCH_LATEST_TAG" = "yes" ]; then
        DOCKERCLOUD_NAMESPACE=checkmk docker push "$REGISTRY$FOLDER/check-mk-${EDITION}:${BRANCH}-latest"
    fi

    if [ "$SET_LATEST_TAG" = "yes" ]; then
        DOCKERCLOUD_NAMESPACE=checkmk docker push "$REGISTRY$FOLDER/check-mk-${EDITION}:latest"
    fi
}

build_image() {
   log "Unpack source tar to $TMP_PATH"
   tar -xz -C "$TMP_PATH" -f "${SOURCE_PATH}/check-mk-${EDITION}-${VERSION}${SUFFIX}.tar.gz"

   log "Copy debian package..."
   cp "${SOURCE_PATH}/${PKG_FILE}" "$DOCKER_PATH/"

   log "Building container image"
   make -C "$DOCKER_PATH" VERSION_TAG=${VERSION_TAG} "$DOCKER_IMAGE_ARCHIVE"

   log "Verschiebe Image-Tarball..."
   mv -v "$DOCKER_PATH/$DOCKER_IMAGE_ARCHIVE" "${SOURCE_PATH}/"

   if [ $EDITION = raw ] || [ "$EDITION" = free ]; then
       docker_tag "" "checkmk"
   else
       docker_tag "registry.checkmk.com" "/${EDITION}"
   fi
}

push_image() {
   if [ "$EDITION" = raw ] || [ "$EDITION" = free ]; then
       docker_push "" "checkmk"
   else
       docker_push "registry.checkmk.com" "/${EDITION}"
   fi

}

if [ "$1" = "-h" ] || [ "$1" = "--help" ] || [ "$1" = "" ] || [ "$2" = "" ] || [ "$3" = "" ] || [ "$4" = "" ] || [ "$5" = "" ] || [ "$6" = "" ] || [ "$7" = "" ]; then
    echo "Aufrufen: build-cmk-container.sh [BRANCH] [EDITION] [VERSION] [SOURCE_PATH] [SET_LATEST_TAG] [SET_BRANCH_LATEST_TAG] [ACTION]"
    echo "          build-cmk-container.sh 2.1.0 enterprise 2.1.0p6 /foo/bar/2.1.0p6-rc1 no no push"
    echo
    exit 1
fi

BRANCH=$1
EDITION=$2
VERSION=$3
SOURCE_PATH=$4
SET_LATEST_TAG=$5
SET_BRANCH_LATEST_TAG=$6
ACTION=$7

VERSION_TAG=$(basename ${SOURCE_PATH})

if [ $EDITION = raw ]; then
    SUFFIX=.cre
elif [ $EDITION = free ]; then
    SUFFIX=.cfe
elif [ $EDITION = enterprise ]; then
    SUFFIX=.cee
elif [ $EDITION = managed ]; then
    SUFFIX=.cme
elif [ $EDITION = plus ]; then
    SUFFIX=.cpe
else
    die "FEHLER: Unbekannte Edition '$EDITION'"
fi

BASE_PATH=$(pwd)/tmp
mkdir -p "$BASE_PATH"
TMP_PATH=$(mktemp --directory -p $BASE_PATH --suffix=.cmk-docker)
DOCKER_PATH="$TMP_PATH/check-mk-${EDITION}-${VERSION}${SUFFIX}/docker"
DOCKER_IMAGE_ARCHIVE="check-mk-${EDITION}-docker-${VERSION}.tar.gz"
PKG_NAME="check-mk-${EDITION}-${VERSION}"
PKG_FILE="${PKG_NAME}_0.jammy_$(dpkg --print-architecture).deb"



if [ -n "$NEXUS_USERNAME" ] ; then
    log "Log into artifacts.lan.tribe29.com:4000"
    docker login "artifacts.lan.tribe29.com:4000" -u "${NEXUS_USERNAME}" -p "${NEXUS_PASSWORD}"
fi

if [ $ACTION = build ]; then
    build_image
elif [ $ACTION = push ]; then
    push_image
else
    die "FEHLER: Unbekannte action '$ACTION'"
fi
