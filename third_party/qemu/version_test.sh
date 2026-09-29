#!/bin/bash
# version.bzl names the archive the recipe builds: sources.txt (QEMU's version)
# and create-archive's REVISION. Bumping one without the other would otherwise
# only fail in the build-qemu-from-source job.
set -euo pipefail

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
pinned="$(sed -n 's/^ *name = "\(.*\)",$/\1/p' "${HERE}/version.bzl")"
built="$("${HERE}/create-archive" --print-name)"
if [ "${pinned}" != "${built}" ]; then
    echo "error: version.bzl names ${pinned}, but sources.txt and REVISION in" >&2
    echo "       create-archive make it ${built}" >&2
    exit 1
fi
