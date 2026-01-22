#!/bin/bash
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# Merges all bazel xunit output files to a single directory hierarchy.

BAZEL_BIN_PATH=$(bazel info bazel-bin)
BAZEL_TEST_LOGS_SRC=$(dirname "$(dirname "$BAZEL_BIN_PATH")")
BAZEL_TEST_LOGS_DEST="${BAZEL_TEST_LOGS_DEST:-../results}"

if [ -z "${BAZEL_TEST_LOGS_SRC}" ]; then
    echo BAZEL_TEST_LOGS_SRC is empty!
    exit 1
fi

if [ -z "${BAZEL_TEST_LOGS_DEST}" ]; then
    echo BAZEL_TEST_LOGS_DEST is empty!
    exit 2
fi

RSYNC_PATH=$(command -v rsync)
if [ -z "${RSYNC_PATH}" ]; then
    echo Could not find rsync!
    exit 3
fi

if [ ! -d "${BAZEL_TEST_LOGS_DEST}" ]; then
    echo "Making destination directory ${BAZEL_TEST_LOGS_DEST}."
    mkdir --parents "${BAZEL_TEST_LOGS_DEST}"
fi

${RSYNC_PATH} --recursive \
    --checksum \
    --copy-links \
    --perms \
    --times \
    --group \
    --owner \
    --checksum \
    --prune-empty-dirs \
    --include='**/test.xml' \
    --include='**/' \
    --exclude='*' \
    "${BAZEL_TEST_LOGS_SRC}" \
    "${BAZEL_TEST_LOGS_DEST}"

exit $?
