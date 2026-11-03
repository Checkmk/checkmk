#!/bin/bash
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# Publishing to the Nexus upstream-archives mirror, shared by the jobs that
# put pinned artifacts there (build_qemu.sh, agents/wnx/test-vm/upload-image.sh).
# Sourced, not executed. The caller runs nexus_init, removes $NETRC on exit,
# and calls write_netrc before anything else. Published files are never
# overwritten: upstream-archives refuses redeploys.

# Sets NEXUS_UPSTREAM_URL, the repository URL without a trailing slash
# (unless given: the mirror Bazel fetches pins from), and NETRC, a private
# file for the credentials.
nexus_init() {
    local root
    root="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
    NEXUS_UPSTREAM_URL="${NEXUS_UPSTREAM_URL:-$(sed -n 's|^UPSTREAM_MIRROR_URL = "\(.*\)/"$|\1|p' "${root}/bazel_variables.bzl")}"
    if [ -z "${NEXUS_UPSTREAM_URL}" ]; then
        echo "error: cannot read UPSTREAM_MIRROR_URL from bazel_variables.bzl" >&2
        exit 1
    fi
    NETRC="$(mktemp)"
}

netrc_quote() {
    local s="${1//\\/\\\\}"
    printf '"%s"' "${s//\"/\\\"}"
}

# Keeps the Nexus credentials off curl's command line (ps).
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
# than passing for "not published".
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

# <file> [<name>]: publishes the file under its basename, or under <name>.
# Callers check nexus_exists first.
upload_nexus() {
    local name="${2:-$(basename "$1")}"
    printf "Upload (Nexus): %s\n" "${name}"
    # No "Expect: 100-continue" (curl's default above 1 MiB): Nexus answers
    # 408 to it instead of 100.
    curl -sSf --netrc-file "${NETRC}" -H 'Expect:' --upload-file "$1" \
        "${NEXUS_UPSTREAM_URL}/${name}"
}
