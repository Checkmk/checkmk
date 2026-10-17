#!/bin/bash
#
# Build the static QEMU and publish the tarball pinned by @qemu_linux_x86_64
# (third_party/qemu/version.bzl) to the Nexus upstream-archives mirror,
# together with every source tarball it was built from (sources.txt): the
# corresponding source of the GPL/LGPL code linked into it, and what a
# rebuild fetches first, whatever happens upstream.
#
# The build lives in third_party/qemu/create-archive; this script adds the
# "build, check the pin, publish what is missing" plumbing.
# It runs in the builder image (third_party/qemu/builder-image.txt), see
# buildscripts/scripts/build-qemu-from-source.groovy.
#
# The recipe is reproducible, so the pin is computed from a local build and
# committed before this job runs: an archive that does not match it is not
# published. Published files are never overwritten (upstream-archives also
# refuses redeploys).

set -euo pipefail

REPO_ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
# nexus_init, write_netrc, nexus_exists, nexus_sha256, upload_nexus
# shellcheck source=buildscripts/scripts/nexus_upload.sh disable=SC1091
source "${REPO_ROOT}/buildscripts/scripts/nexus_upload.sh"
RECIPE="${REPO_ROOT}/third_party/qemu"
NAME="$(sed -n 's/^ *name = "\(.*\)",$/\1/p' "${RECIPE}/version.bzl")"
PIN="$(sed -n 's/^ *sha256 = "\(.*\)",$/\1/p' "${RECIPE}/version.bzl")"
if [ -z "${NAME}" ] || [ -z "${PIN}" ]; then
    echo "error: cannot read name and sha256 from third_party/qemu/version.bzl" >&2
    exit 1
fi
if [ "${NAME}" != "$("${RECIPE}/create-archive" --print-name)" ]; then
    echo "error: version.bzl names ${NAME}, but sources.txt and REVISION in create-archive" >&2
    echo "       make it $("${RECIPE}/create-archive" --print-name)" >&2
    exit 1
fi
ARCHIVE="${NAME}.tar.xz"

nexus_init
if [ -n "${WORKDIR:-}" ]; then
    # For local debugging, won't clean up after itself.
    mkdir -p "${WORKDIR}"
    trap 'rm -f "${NETRC}"' EXIT
else
    WORKDIR="$(mktemp -d)"
    trap 'rm -rf "${WORKDIR}" "${NETRC}"' EXIT
fi

main() {
    write_netrc

    # A source already on Nexus must be the file sources.txt names (say after
    # a hand upload): Nexus refuses redeploys, so only an admin can replace it.
    local sha file nexus missing=()
    while read -r sha file _; do
        case "${sha}" in "" | "#"*) continue ;; esac
        if ! nexus_exists "${file}"; then
            missing+=("${file}")
            continue
        fi
        nexus="$(nexus_sha256 "${file}")"
        if [ "${nexus}" != "${sha}" ]; then
            cat >&2 <<EOF
error: Nexus has ${file} with sha256 ${nexus:-(none found)},
       sources.txt names ${sha}. Have a Nexus admin delete it;
       the next run uploads a verified copy.
EOF
            exit 1
        fi
    done <"${RECIPE}/sources.txt"

    # Every run builds, also when the archive is already published: a recipe
    # changed without a new REVISION and pin would otherwise pass unnoticed.
    (cd "${WORKDIR}" && MIRROR="${NEXUS_UPSTREAM_URL}" "${RECIPE}/create-archive")
    sha="$(sha256sum "${WORKDIR}/${ARCHIVE}" | cut -d' ' -f1)"
    if [ "${sha}" != "${PIN}" ]; then
        cat >&2 <<EOF
error: this recipe builds ${ARCHIVE} with sha256 ${sha},
       third_party/qemu/version.bzl pins ${PIN}. A changed recipe or
       toolchain needs a new REVISION and a pin from a local build.
EOF
        exit 1
    fi

    # The sources before the archive: it is never published without them.
    for file in "${missing[@]}"; do
        upload_nexus "${WORKDIR}/sources/${file}"
    done
    if nexus_exists "${ARCHIVE}"; then
        sha="$(nexus_sha256 "${ARCHIVE}")"
        if [ "${sha}" != "${PIN}" ]; then
            cat >&2 <<EOF
error: Nexus has ${ARCHIVE} with sha256 ${sha:-(none found)},
       third_party/qemu/version.bzl pins ${PIN}. A changed archive
       needs a new name: bump REVISION in create-archive.
EOF
            exit 1
        fi
        printf "Already published, and this recipe reproduces it: %s\n" "${ARCHIVE}"
    else
        upload_nexus "${WORKDIR}/${ARCHIVE}"
    fi
    printf "Pinned in third_party/qemu/version.bzl: %s/%s (sha256 %s)\n" \
        "${NEXUS_UPSTREAM_URL}" "${ARCHIVE}" "${PIN}"
}

main "$@"
