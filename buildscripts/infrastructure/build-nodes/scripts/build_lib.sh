#!/bin/bash

log() {
    echo "+++ $1"
}

_artifact_name() {
    local DIR_NAME="$1"
    local DISTRO="$2"
    local BRANCH_VERSION="$3"
    local BUILD_ID="$4"
    echo "${DIR_NAME}_${BUILD_ID}_${BRANCH_VERSION}_${DISTRO}.tar.gz"
}

_download_from_mirror() {
    local TARGET_PATH=$1
    local MIRROR_URL=$2

    log "Downloading ${MIRROR_URL}"
    curl -1 -sSf -o "${TARGET_PATH}" "${MIRROR_URL}" || return
    log "Got ${TARGET_PATH} file from ${MIRROR_URL}"
}

_download_from_upstream() {
    local TARGET_PATH=$1
    local UPSTREAM_URL=$2
    curl -1 -sSfL -o "${TARGET_PATH}" "${UPSTREAM_URL}"
    log "Got ${TARGET_PATH} file from ${UPSTREAM_URL}"
}

_upload_to_mirror() {
    local TARGET_PATH=$1
    local MIRROR_BASE_URL=$2
    local MIRROR_CREDENTIALS=$3

    if [ -z "${MIRROR_CREDENTIALS}" ]; then
        log "No credentials given, not uploading, continuing with build ..."
        return
    fi

    log "Uploading ${TARGET_PATH} to ${MIRROR_BASE_URL}"
    if ! curl -sSf -u "${MIRROR_CREDENTIALS}" --upload-file "${TARGET_PATH}" "${MIRROR_BASE_URL}"; then
        log "Upload failed, continuing with build ..."
        return
    fi

    log "Upload done"
}

# Use this function to transparently download an external file using our HTTP
# mirror as caching server
mirrored_download() {
    local TARGET_PATH=$1
    local FILE_NAME="${TARGET_PATH##*/}"
    local UPSTREAM_URL=$2

    # Get mirror related information from the environment
    if [ -z "${NEXUS_ARCHIVES_URL}" ]; then
        log "ERROR: NEXUS_ARCHIVES_URL not set"
        exit 1
    fi
    if [ -z "${NEXUS_USERNAME}" ]; then
        log "ERROR: NEXUS_USERNAME not set"
        exit 1
    fi
    if [ -z "${NEXUS_PASSWORD}" ]; then
        log "ERROR: NEXUS_PASSWORD not set"
        exit 1
    fi
    local MIRROR_BASE_URL=${NEXUS_ARCHIVES_URL}
    local MIRROR_URL=${MIRROR_BASE_URL}$FILE_NAME
    local MIRROR_CREDENTIALS="${NEXUS_USERNAME}:${NEXUS_PASSWORD}"

    if ! _download_from_mirror "${TARGET_PATH}" "${MIRROR_URL}"; then
        log "File not available from ${MIRROR_URL}, downloading from ${UPSTREAM_URL}"

        _download_from_upstream "${TARGET_PATH}" "${UPSTREAM_URL}"
        _upload_to_mirror "${TARGET_PATH}" "${MIRROR_BASE_URL}" "${MIRROR_CREDENTIALS}"
    fi
}

_unpack_package() {
    local ARCHIVE_PATH="$1"
    local TARGET_DIR="$2"

    log "Unpacking ${ARCHIVE_PATH}"
    tar -xz -C "${TARGET_DIR}" -f "${ARCHIVE_PATH}"
}

_cleanup_package() {
    local ARCHIVE_PATH="$1"
    log "Cleaning up ${ARCHIVE_PATH}"
    rm -f "${ARCHIVE_PATH}"
}

_create_package() {
    local ARCHIVE_PATH="$1"
    local TARGET_DIR="$2"
    local DIR_NAME="$3"

    log "Creating ${ARCHIVE_PATH} from ${TARGET_DIR}/${DIR_NAME}"
    tar -cz -C "${TARGET_DIR}" -f "${ARCHIVE_PATH}" "${DIR_NAME}"
}

# Use this function to trigger a build action or use an already pre-built artifact
cached_build() {
    local TARGET_DIR="$1"
    local DIR_NAME="$2"
    local BUILD_ID="$3"
    local DISTRO="$4"
    local BRANCH_VERSION="$5"

    if ! type -t build_package; then
        log "ERROR: build_package function not defined"
        exit 1
    fi

    if [ -z "$DISTRO" ]; then
        log "ERROR: DISTRO not set"
        exit 1
    fi

    if [ -z "${BRANCH_VERSION}" ]; then
        log "ERROR: BRANCH_VERSION not set"
        exit 1
    fi

    local FILE_NAME="$(_artifact_name "${DIR_NAME}" "${DISTRO}" "${BRANCH_VERSION}" "${BUILD_ID}")"
    local ARCHIVE_PATH="${TARGET_DIR}/${FILE_NAME}"
    log "Artifact: ${FILE_NAME}"

    # Get mirror related information from the environment
    if [ -z "${NEXUS_ARCHIVES_URL}" ]; then
        log "ERROR: NEXUS_ARCHIVES_URL not set"
        exit 1
    fi
    if [ -z "${NEXUS_USERNAME}" ]; then
        log "ERROR: NEXUS_USERNAME not set"
        exit 1
    fi
    if [ -z "${NEXUS_PASSWORD}" ]; then
        log "ERROR: NEXUS_PASSWORD not set"
        exit 1
    fi
    local MIRROR_BASE_URL=${NEXUS_ARCHIVES_URL}
    local MIRROR_URL=${MIRROR_BASE_URL}$FILE_NAME
    local MIRROR_CREDENTIALS="${NEXUS_USERNAME}:${NEXUS_PASSWORD}"

    if _download_from_mirror "${ARCHIVE_PATH}" "${MIRROR_URL}"; then
        _unpack_package "${ARCHIVE_PATH}" "${TARGET_DIR}"
    else
        build_package
        _create_package "${ARCHIVE_PATH}" "${TARGET_DIR}" "${DIR_NAME}"
        _upload_to_mirror "${ARCHIVE_PATH}" "${MIRROR_BASE_URL}" "${MIRROR_CREDENTIALS}"
    fi

    _cleanup_package "${ARCHIVE_PATH}"
}
