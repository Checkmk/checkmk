#!/bin/bash
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# Check for accidentally added/kept non-free files and return non-zero on findings

set -e -o pipefail

if [ -z "$*" ]; then
    echo >&2 "$0 PACKAGE..."
    echo >&2 "Example: $0 /path/to/package.tar.gz"
    exit 1
fi

for SRC_PATH in "$@"; do
    FILENAME="${SRC_PATH##*/}"
    DIRNAME="${FILENAME%.tar.gz}"
    echo "=> $SRC_PATH"

    FORBIDDEN_FILES="$(tar tvzf "$SRC_PATH" | grep -E "$DIRNAME/(cloud|managed|enterprise|saas)/.+" || true)"
    if [ -n "$FORBIDDEN_FILES" ]; then
        echo >&2 "ERROR: found files which must not be part of source package:"
        for path in ${FORBIDDEN_FILES}; do
            echo >&2 "  $path"
        done
        exit 1
    fi
    echo "Done."
done
