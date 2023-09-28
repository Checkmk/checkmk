#!/bin/bash
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# Remove source files of enterprise / managed / cloud specific components from the
# given source archives before publishing them

set -e -o pipefail

if [ -z "$*" ]; then
    echo "$0 PACKAGE..."
    echo "Example: $0 /path/to/package.tar.gz"
    exit 1
fi

for SRC_PATH in "$@"; do
    FILENAME="${SRC_PATH##*/}"
    DIRNAME="${FILENAME%.tar.gz}"
    REMOVE_DIRS=""
    echo "=> $SRC_PATH"

    if tar tvzf "$SRC_PATH" | grep -E "$DIRNAME/saas/.+" >/dev/null; then
        echo "Found CSE specific components..."
        REMOVE_DIRS+=" $DIRNAME/saas/*"
    fi

    if tar tvzf "$SRC_PATH" | grep -E "$DIRNAME/cloud/.+" >/dev/null; then
        echo "Found CCE specific components..."
        REMOVE_DIRS+=" $DIRNAME/cloud/*"
    fi

    if tar tvzf "$SRC_PATH" | grep -E "$DIRNAME/managed/.+" >/dev/null; then
        echo "Found CME specific components..."
        REMOVE_DIRS+=" $DIRNAME/managed/*"
    fi

    if tar tvzf "$SRC_PATH" | grep -E "$DIRNAME/enterprise/.+" >/dev/null; then
        echo "Found CEE specific components..."
        REMOVE_DIRS+=" $DIRNAME/enterprise/*"
    fi

    if [ -z "$REMOVE_DIRS" ]; then
        echo "Found no files to be removed. Done."
        continue
    fi

    echo "Removing$REMOVE_DIRS..."
    # shellcheck disable=SC2086 # Double quote to prevent globbing and word splitting.
    gunzip -c "$SRC_PATH" | tar -v --wildcards --delete$REMOVE_DIRS | gzip >"$SRC_PATH.new"
    mv "$SRC_PATH.new" "$SRC_PATH"

    echo "Checking for remaining CEE/CME/CCE/CSE files..."
    if tar tvzf "$SRC_PATH" | grep -E "$DIRNAME/(cloud|managed|enterprise|saas)/.+"; then
        echo "ERROR: Still found some CEE/CME specific components."
        exit 1
    fi
    echo "Done."
done
