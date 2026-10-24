#!/bin/bash
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# Publishes a Windows test VM image built by make_image.py to the Nexus
# upstream-archives mirror under a versioned name, and prints what goes into
# agents/wnx/test-vm/image.bzl. Published names are never overwritten: older
# pins keep resolving.
#
# Usage: upload-image.sh <image.qcow2> <name>   (NEXUS_USERNAME/NEXUS_PASSWORD)
#        upload-image.sh --check <name>
#   e.g. name: win2022-core-2026-09-28-2048.qcow2
# The Eval expiry comes from <image.qcow2>.expires, which make_image.py writes.
# --check only tests that Nexus accepts the credentials and that <name> is
# still free, before a build that takes half an hour. It cannot tell whether
# they may also upload: Nexus has no dry run.

set -euo pipefail

if [ "${1:-}" = --check ]; then
    IMAGE=''
    NAME=${2:?versioned name}
else
    IMAGE=${1:?image.qcow2}
    NAME=${2:?versioned name}
fi
REPO_ROOT="$(cd "$(dirname "$0")/../../.." && pwd)"
# nexus_init, write_netrc, nexus_exists, nexus_sha256, upload_nexus
# shellcheck source=buildscripts/scripts/nexus_upload.sh disable=SC1091
source "${REPO_ROOT}/buildscripts/scripts/nexus_upload.sh"
nexus_init
trap 'rm -f "${NETRC}"' EXIT

write_netrc
if nexus_exists "$NAME"; then
    echo "error: $NAME is already published; pick a new name" >&2
    exit 1
fi
if [ -z "$IMAGE" ]; then
    echo "Nexus credentials OK, $NAME is free"
    exit 0
fi
EXPIRES=$(cat "$IMAGE.expires")
SHA256=$(sha256sum "$IMAGE" | cut -d' ' -f1)
# Large uploads have failed and succeeded on a retry. Nexus may have stored
# the file anyway, and then refuses a second upload: retry only while the
# name does not exist yet; the checksum below decides.
for attempt in 1 2 3; do
    upload_nexus "$IMAGE" "$NAME" && break
    # In a subshell: nexus_exists exits on an answer other than 200 or 404,
    # which a Nexus that is still down gives.
    (nexus_exists "$NAME") && break
    [ "$attempt" = 3 ] && {
        echo "error: uploading $NAME failed" >&2
        exit 1
    }
    sleep 30
done
# What Nexus stored, by its own checksum: no need to fetch 5 GB back. Its
# search index may lag behind the upload, by minutes when it is busy.
STORED=''
for _ in $(seq 180); do
    STORED=$(nexus_sha256 "$NAME") || STORED=''
    [ -n "$STORED" ] && break
    sleep 10
done
if [ -z "$STORED" ]; then
    # The upload went through, and the name is taken now.
    echo "error: $NAME is uploaded, but Nexus's search index has no sha256 for it after 30 min." >&2
    echo "       Once it has, check it against the local image's $SHA256" >&2
    echo "       and pin file = \"$NAME\", sha256 = \"$SHA256\", expires = \"$EXPIRES\"." >&2
    exit 1
fi
[ "$STORED" = "$SHA256" ] || {
    echo "error: Nexus has $NAME with sha256 $STORED, the local image is $SHA256" >&2
    exit 1
}
echo "published $NEXUS_UPSTREAM_URL/$NAME"
cat <<EOF
image.bzl:
    file = "$NAME",
    sha256 = "$SHA256",
    expires = "$EXPIRES",
EOF
