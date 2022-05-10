#!/bin/bash
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

set -ex
unset LANG

log() { echo "[$(date '+%F %T')] ==============================" "$@"; }
die() { log "$@"; exit 1; }

# Tag Containers and push them to a Registry
docker_push () {
    REGISTRY=$1
    FOLDER=$2

    log "Erstelle \"${VERSION}\" tag..."
    docker tag "checkmk/check-mk-${EDITION}${DEMO}:${VERSION}" "$REGISTRY$FOLDER/check-mk-${EDITION}${DEMO}:${VERSION}"

    log "Erstelle \"{$BRANCH}-latest\" tag..."
    docker tag "checkmk/check-mk-${EDITION}${DEMO}:${VERSION}" "$REGISTRY$FOLDER/check-mk-${EDITION}${DEMO}:${BRANCH}-latest"

    log "Erstelle \"latest\" tag..."
    docker tag "checkmk/check-mk-${EDITION}${DEMO}:${VERSION}" "$REGISTRY$FOLDER/check-mk-${EDITION}${DEMO}:latest"

    log "Lade zu ($REGISTRY) hoch..."
    docker login ${REGISTRY} -u ${DOCKER_USERNAME} -p ${DOCKER_PASSPHRASE}
    DOCKERCLOUD_NAMESPACE=checkmk docker push "$REGISTRY$FOLDER/check-mk-${EDITION}${DEMO}:${VERSION}"
    DOCKERCLOUD_NAMESPACE=checkmk docker push "$REGISTRY$FOLDER/check-mk-${EDITION}${DEMO}:${BRANCH}-latest"
    if [ "$SET_LATEST_TAG" = "yes" ]; then
        DOCKERCLOUD_NAMESPACE=checkmk docker push "$REGISTRY$FOLDER/check-mk-${EDITION}${DEMO}:latest"
    fi
}

if [ "$1" = "-h" ] || [ "$1" = "--help" ] || [ "$1" = "" ] || [ "$2" = "" ] || [ "$3" = "" ] || [ "$4" = "" ]; then
    echo "Aufrufen: bw-docker-bauen [BRANCH] [EDITION] [VERSION] [SET_LATEST_TAG]"
    echo "          bw-docker-bauen 1.5.0 enterprise 1.5.0p4 no no"
    echo
    exit 1
fi

BRANCH=$1
EDITION=$2
VERSION=$3
SET_LATEST_TAG=$4

if [ $EDITION = raw ]; then
    SUFFIX=.cre
elif [ $EDITION = free ]; then
    SUFFIX=.cfe
elif [ $EDITION = enterprise ]; then
    SUFFIX=.cee
elif [ $EDITION = managed ]; then
    SUFFIX=.cme
else
    die "FEHLER: Unbekannte Edition '$EDITION'"
fi

BASE_PATH=$(pwd)/tmp
mkdir -p "$BASE_PATH"
TMP_PATH=$(mktemp --directory -p $BASE_PATH --suffix=.cmk-docker)
PACKAGE_PATH=$(pwd)/download
DOCKER_PATH="$TMP_PATH/check-mk-${EDITION}-${VERSION}${SUFFIX}${DEMO}/docker"
DOCKER_IMAGE_ARCHIVE="check-mk-${EDITION}-docker-${VERSION}${DEMO}.tar.gz"
PKG_NAME="check-mk-${EDITION}-${VERSION}${DEMO}"
PKG_FILE="${PKG_NAME}_0.buster_$(dpkg --print-architecture).deb"

trap "rm -rf \"$TMP_PATH\"" SIGTERM SIGHUP SIGINT


if [ -n "$NEXUS_USERNAME" ] ; then
    log "Log into artifacts.lan.tribe29.com:4000"
    docker login "artifacts.lan.tribe29.com:4000" -u "${NEXUS_USERNAME}" -p "${NEXUS_PASSWORD}"
fi

log "Unpack source tar to $TMP_PATH"
tar -xz -C "$TMP_PATH" -f "$PACKAGE_PATH/${VERSION}/check-mk-${EDITION}-${VERSION}${SUFFIX}${DEMO}.tar.gz"

log "Copy debian package..."
cp "$PACKAGE_PATH/${VERSION}/${PKG_FILE}" "$DOCKER_PATH/"

log "Building container image"
make -C "$DOCKER_PATH" "$DOCKER_IMAGE_ARCHIVE"

log "Verschiebe Image-Tarball..."
mv -v "$DOCKER_PATH/$DOCKER_IMAGE_ARCHIVE" "$PACKAGE_PATH/${VERSION}/"

if [ "$EDITION" = raw ] || [ "$EDITION" = free ]; then
    docker_push "" "checkmk"
else
    docker_push "registry.checkmk.com" "/${EDITION}"
fi

log "Räume temporäres Verzeichnis $TMP_PATH weg"
rm -rf "$TMP_PATH"


