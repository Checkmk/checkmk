#!/bin/bash
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

bazel test \
    --test_verbose_timeout_warnings \
    --test_env=TZ='America/Chicago' \
    --test_tag_filters=-component,-cpp \
    --keep_going \
    --//:use_faked_artifacts=true \
    --cmk_edition=ultimate \
    -- //...
