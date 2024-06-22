#!/bin/bash

log() {
    echo "+++ $1"
}

failure() {
    echo "$(basename "$0"):" "$@" >&2
    exit 1
}

# some style settings defined here
txtRed=$'\e[41m'
txtGreen=$'\e[32m'
txtBlue=$'\e[34m'
resetColor=$'\e[0m'

print_red() {
    printf "%s%s%s\n" "${txtRed}" "$1" "${resetColor}"
}

print_green() {
    printf "%s%s%s\n" "${txtGreen}" "$1" "${resetColor}"
}

print_blue() {
    printf "%s%s%s\n" "${txtBlue}" "$1" "${resetColor}"
}

print_debug() {
    print_blue "    $1"
}

get_desired_python_version() {
    # to use "make print-PYTHON_VERISON" the git repo with "Makefile" and "artifacts.make" would be necessary at a known location
    sed -n 's|^PYTHON_VERSION = \"\(\S*\)\"$|\1|p' "${1}"/package_versions.bzl
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
    local MIRROR_CREDENTIALS=$3

    if [ -z "${MIRROR_CREDENTIALS}" ]; then
        log "No credentials given, not downloading, continuing with build ..."
        return
    fi

    log "Downloading ${MIRROR_URL}"
    curl -u "${MIRROR_CREDENTIALS}" -1 -sSf -o "${TARGET_PATH}" "${MIRROR_URL}" || return
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

    if ! _download_from_mirror "${TARGET_PATH}" "${MIRROR_URL}" "${MIRROR_CREDENTIALS}"; then
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

    local FILE_NAME
    FILE_NAME="$(_artifact_name "${DIR_NAME}" "${DISTRO}" "${BRANCH_VERSION}" "${BUILD_ID}")"
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

    if _download_from_mirror "${ARCHIVE_PATH}" "${MIRROR_URL}" "${MIRROR_CREDENTIALS}"; then
        _unpack_package "${ARCHIVE_PATH}" "${TARGET_DIR}"
    else
        build_package
        _create_package "${ARCHIVE_PATH}" "${TARGET_DIR}" "${DIR_NAME}"
        _upload_to_mirror "${ARCHIVE_PATH}" "${MIRROR_BASE_URL}" "${MIRROR_CREDENTIALS}"
    fi

    _cleanup_package "${ARCHIVE_PATH}"
}

set_bin_symlinks() {
    local TARGET_DIR="$1"
    local DIR_NAME="$2"

    log "Make binaries from ${TARGET_DIR}/${DIR_NAME}/bin available via ${TARGET_DIR}/bin"
    mkdir -p "${TARGET_DIR}/bin"
    ln -sf "${TARGET_DIR}/${DIR_NAME}/bin/"* "${TARGET_DIR}/bin"
}

# When building our build containers we don't have the whole repo available,
# but we copy defines.make to scripts (see build-build-containers.jenkins).
# However, in other situations we have the git available and need to find
# defines.make in the repo base directory.
find_defines_make() {
    local SEARCH_PATH="$1"
    cd "$SEARCH_PATH" || true
    while [ ! -e defines.make ]; do
        if [ "$PWD" = / ]; then
            failure "could not find defines.make"
        fi
        cd ..
    done
    echo "$PWD/defines.make"
}

get_version() {
    local SEARCH_PATH="$1"
    local NAME="$2"
    make --no-print-directory --file="$(find_defines_make "$SEARCH_PATH")" print-"$NAME"
}

test_package() {
    log "Testing for ${1% *} in \$PATH"
    CMD_OUTPUT="$($1 2>&1 || true)"
    echo "$CMD_OUTPUT" | grep "$2" >/dev/null || (
        echo "Invalid output of \"$1\": \"$($1)\" was expected to match with grep \"$2\""
        exit 1
    )
}
