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
# The mirror Bazel fetches the pin from.
NEXUS_UPSTREAM_URL="${NEXUS_UPSTREAM_URL:-$(sed -n 's|^UPSTREAM_MIRROR_URL = "\(.*\)/"$|\1|p' "${REPO_ROOT}/bazel_variables.bzl")}"
if [ -z "${NEXUS_UPSTREAM_URL}" ]; then
    echo "error: cannot read UPSTREAM_MIRROR_URL from bazel_variables.bzl" >&2
    exit 1
fi
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

# Keeps the Nexus credentials off curl's command line (ps).
NETRC="$(mktemp)"
if [ -n "${WORKDIR:-}" ]; then
    # For local debugging, won't clean up after itself.
    mkdir -p "${WORKDIR}"
    trap 'rm -f "${NETRC}"' EXIT
else
    WORKDIR="$(mktemp -d)"
    trap 'rm -rf "${WORKDIR}" "${NETRC}"' EXIT
fi

netrc_quote() {
    local s="${1//\\/\\\\}"
    printf '"%s"' "${s//\"/\\\"}"
}

write_netrc() {
    if [ -z "${NEXUS_USERNAME:-}" ] || [ -z "${NEXUS_PASSWORD:-}" ]; then
        echo "error: Nexus credentials missing" >&2
        exit 1
    fi
    local host="${NEXUS_UPSTREAM_URL#*://}"
    host="${host%%/*}"
    # printf is a builtin: the password never shows up in an argv.
    printf 'machine %s login %s password %s\n' "${host%%:*}" \
        "$(netrc_quote "${NEXUS_USERNAME}")" "$(netrc_quote "${NEXUS_PASSWORD}")" >"${NETRC}"
}

# Anything but 200 or 404 (bad credentials, Nexus down) stops the job, rather
# than passing for "not published" and starting a build.
nexus_exists() {
    local code
    code="$(curl -sS -o /dev/null -w '%{http_code}' -I --netrc-file "${NETRC}" \
        "${NEXUS_UPSTREAM_URL}/$1")" || true
    case "${code}" in
        200) return 0 ;;
        404) return 1 ;;
        *)
            echo "error: HEAD ${NEXUS_UPSTREAM_URL}/$1 returned HTTP ${code}" >&2
            exit 1
            ;;
    esac
}

# The sha256 Nexus recorded for a published file, from its search API (the
# repository itself serves no checksum files); empty if the search finds none.
nexus_sha256() {
    local repo="${NEXUS_UPSTREAM_URL##*/repository/}"
    curl -sSf -G --netrc-file "${NETRC}" "${NEXUS_UPSTREAM_URL%/repository/*}/service/rest/v1/search/assets" \
        --data-urlencode "repository=${repo%%/*}" --data-urlencode "name=/$1" |
        python3 -c 'import json, sys; print(*(i["checksum"]["sha256"] for i in json.load(sys.stdin)["items"]))'
}

# Callers check nexus_exists first: upstream-archives refuses redeploys.
upload_nexus() {
    printf "Upload (Nexus): %s\n" "$(basename "$1")"
    # No "Expect: 100-continue" (curl's default above 1 MiB): Nexus answers
    # 408 to it instead of 100.
    curl -sSf --netrc-file "${NETRC}" -H 'Expect:' --upload-file "$1" \
        "${NEXUS_UPSTREAM_URL}/$(basename "$1")"
}

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
