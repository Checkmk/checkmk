#!/bin/sh
#
# Build Wine from source and publish the tarball pinned by @wine_linux_x86_64
# to the Nexus upstream-archives mirror. This is the from-source replacement
# for the prebuilt Kron4ek binary.
#
# The actual build lives in third_party/wine/create-archive; this script
# installs the build toolchain on demand, then handles the "build once,
# publish, skip if already published" plumbing.
#
# It runs in the wine-builder image (third_party/wine/Dockerfile) which has the
# Wine build toolchain baked in on top of the AlmaLinux 8 base (glibc floor
# 2.28), so no privileged/yum step is needed here. See
# buildscripts/scripts/build-wine-from-source.groovy.
#
# The corresponding LGPL source (wine-<version>.tar.xz) is published alongside
# the binary, so a download of the binary is accompanied by its source
# (LGPL-2.1 section 4).
#
# TODO: also publish to the public CI binary-artifacts S3 bucket (for external
# contributors) once its credentials (aws_ci_binary_artifacts_*) are registered
# in Jenkins. The bucket object schema mirrors buildscripts/scripts/extract_llvm.sh:
# dl/<publisher>/wine/<version>/linux/x86_64/<variant>/<file>.

set -eu

WINE_VERSION="11.0"
VARIANT="amd64-wow64"
ARCHIVE_NAME="wine-${WINE_VERSION}-${VARIANT}.tar.xz"
# Corresponding LGPL source, published alongside the binary.
SOURCE_NAME="wine-${WINE_VERSION}.tar.xz"

# Nexus upstream-archives mirror (matches UPSTREAM_MIRROR_URL in MODULE.bazel).
NEXUS_UPSTREAM_URL="${NEXUS_UPSTREAM_URL:-https://artifacts.lan.tribe29.com/repository/upstream-archives}"

REPO_ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
CREATE_ARCHIVE="${REPO_ROOT}/third_party/wine/create-archive"

if [ -n "${WORKDIR:-}" ]; then
    # For local debugging, won't clean-up after itself.
    mkdir -p "$WORKDIR"
else
    WORKDIR="$(mktemp -d)"
    trap 'rm -rf "$WORKDIR"' EXIT
fi

require_credentials() {
    if [ -z "${NEXUS_USERNAME:-}" ] || [ -z "${NEXUS_PASSWORD:-}" ]; then
        echo "Error: Nexus credentials missing" >&2
        exit 1
    fi
}

nexus_exists() {
    curl -sfI -u "${NEXUS_USERNAME}:${NEXUS_PASSWORD}" "$1" >/dev/null 2>&1
}

all_uploaded() {
    nexus_exists "${NEXUS_UPSTREAM_URL}/${ARCHIVE_NAME}" || return 1
    nexus_exists "${NEXUS_UPSTREAM_URL}/${SOURCE_NAME}" || return 1
}

upload_nexus() {
    dest="${NEXUS_UPSTREAM_URL}/$(basename "$1")"
    printf "Upload (Nexus): %s -> %s\n" "$1" "$dest"
    curl -sSf -u "${NEXUS_USERNAME}:${NEXUS_PASSWORD}" --upload-file "$1" "$dest"
}

main() {
    require_credentials

    if all_uploaded; then
        printf "Nothing to do: Wine %s %s artifacts already present.\n" \
            "$WINE_VERSION" "$VARIANT"
        return 0
    fi

    (cd "$WORKDIR" && "$CREATE_ARCHIVE")

    # Binary artifact + its corresponding LGPL source.
    upload_nexus "$WORKDIR/$ARCHIVE_NAME"
    upload_nexus "$WORKDIR/$SOURCE_NAME"
}

main "$@"
