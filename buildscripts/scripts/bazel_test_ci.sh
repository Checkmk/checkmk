#!/bin/bash
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

bep_json=$(mktemp /tmp/bep_XXXXXX.json)
trap 'rm -f "$bep_json"' EXIT

tag_filters="-component${BAZEL_EXTRA_TAG_FILTERS:+,${BAZEL_EXTRA_TAG_FILTERS}}"

RC=0
bazel test \
    --build_event_json_file="$bep_json" \
    --keep_going \
    --//:use_faked_artifacts=true \
    --test_tag_filters="$tag_filters" \
    "$@" || RC=$?

bep_out="$(bazel info bazel-testlogs)"/_bep_output
bazel run //buildscripts/scripts/bep_to_junit "$bep_json" "$bep_out"

exit $RC
