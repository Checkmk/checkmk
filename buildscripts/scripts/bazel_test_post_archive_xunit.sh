#!/bin/bash
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# Merges all bazel xunit output files to a single directory hierarchy.
#
# Paths into the test's runfiles tree of the main repository are made
# relative to the repository root on the way, so tools reading the files
# (e.g. Jenkins warnings-ng) find the sources in the workspace checkout
# instead of in the long-gone sandbox. Paths into other repositories stay.
#
# A path whose first directory is not letters only, like "non-free/", gets
# "tests/../" in front: the JUnit parser of warnings-ng (violations-lib)
# wants a letters-only directory at the start of a relative path and would
# read "non-free/x.py" as "free/x.py". Drop this once that is fixed:
# https://github.com/tomasbjerre/violations-lib/issues/241

BAZEL_TEST_LOGS_SRC=$(bazel info bazel-testlogs)
BAZEL_TEST_LOGS_DEST="${BAZEL_TEST_LOGS_DEST:-../results}"
# Stops at whitespace, quotes, tags, entities (&quot;) and the characters
# that glue a path to its surroundings, like "self=" or "at (".
RUNFILES_MAIN_PREFIX="[^][:space:]\"'<>&;()=:,[]*\.runfiles/_main/"

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

find "${BAZEL_TEST_LOGS_SRC}" -name "test.xml" | while IFS= read -r src; do
    rel="${src#"${BAZEL_TEST_LOGS_SRC}"/}"
    dst="${BAZEL_TEST_LOGS_DEST}/${rel}"
    mkdir -p "$(dirname "$dst")"
    sed -E \
        -e "s#${RUNFILES_MAIN_PREFIX}([a-zA-Z]+/)#\1#g" \
        -e "s#${RUNFILES_MAIN_PREFIX}#tests/../#g" \
        "$src" >"$dst"
done

rc=$?

xml_count=$(find "${BAZEL_TEST_LOGS_DEST}" -name "test.xml" 2>/dev/null | wc -l)
if [ "${xml_count}" -eq 0 ]; then
    echo "WARNING: No test.xml files found in ${BAZEL_TEST_LOGS_DEST}"
fi

exit $rc
