#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.plugins.aws_v2.special_agent.labels import resource_labels


def test_resource_labels_make_the_tags_valid_labels() -> None:
    labels = resource_labels("s3", "bucket", "bucket", "eu-central-1", {"a:b": "", "c": "d:e"})

    assert labels == {
        "cmk/aws/service": "s3",
        "cmk/aws/name": "bucket",
        "cmk/aws/resource_id": "bucket",
        "cmk/aws/region": "eu-central-1",
        "cmk/aws/tag/a_b": "true",
        "cmk/aws/tag/c": "d_e",
    }
