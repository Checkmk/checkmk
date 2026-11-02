#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import json
from collections.abc import Mapping

import pytest

from cmk.agent_based.v2 import CheckResult, Metric, Result, Service, State, StringTable
from cmk.plugins.aws_v2.agent_based.aws_s3 import (
    check_aws_s3_objects,
    discover_aws_s3,
    parse_aws_s3_bucket,
)


def _bucket_string_table(values: Mapping[str, float]) -> StringTable:
    """The section of one bucket host. The keys of values are "<storage class>_<metric>"."""
    rows = [
        {
            "Id": f"id_0_{metric_id}",
            "Label": "my-bucket",
            "Values": [[value, None]],
            "LocationConstraint": "eu-central-1",
            "Tagging": [{"Key": "team", "Value": "cloud"}],
        }
        for metric_id, value in values.items()
    ]
    return [json.dumps(rows).split()]


_BUCKET_VALUES = {
    "StandardStorage_BucketSizeBytes": 1024.0,
    "StandardIAStorage_BucketSizeBytes": 2048.0,
    "AllStorageTypes_NumberOfObjects": 3.0,
}


@pytest.mark.parametrize(
    "values, expected",
    [
        pytest.param(_BUCKET_VALUES, [Service()], id="size and objects -> one service"),
        pytest.param(
            {"StandardStorage_BucketSizeBytes": 1024.0},
            [],
            id="no number of objects metric -> no service",
        ),
    ],
)
def test_discover_aws_s3(values: Mapping[str, float], expected: list[Service]) -> None:
    section = parse_aws_s3_bucket(_bucket_string_table(values))
    assert section is not None
    assert list(discover_aws_s3(section)) == expected


@pytest.mark.parametrize(
    "params, expected",
    [
        pytest.param(
            {},
            [
                Result(state=State.OK, summary="Bucket size: 3.00 KiB"),
                Metric("aws_bucket_size", 3072.0),
                Result(
                    state=State.OK, summary="StandardStorage: 1.00 KiB, StandardIAStorage: 2.00 KiB"
                ),
                Result(state=State.OK, summary="Number of objects: 3"),
                Metric("aws_num_objects", 3.0),
                Result(state=State.OK, summary="Location: eu-central-1"),
                Result(state=State.OK, summary="[Tags] team: cloud"),
            ],
            id="no levels -> OK with size, objects, location and tags",
        ),
        pytest.param(
            {"bucket_size_levels": (2048.0, 4096.0)},
            [
                Result(
                    state=State.WARN,
                    summary="Bucket size: 3.00 KiB (warn/crit at 2.00 KiB/4.00 KiB)",
                ),
                Metric("aws_bucket_size", 3072.0, levels=(2048.0, 4096.0)),
                Result(
                    state=State.OK, summary="StandardStorage: 1.00 KiB, StandardIAStorage: 2.00 KiB"
                ),
                Result(state=State.OK, summary="Number of objects: 3"),
                Metric("aws_num_objects", 3.0),
                Result(state=State.OK, summary="Location: eu-central-1"),
                Result(state=State.OK, summary="[Tags] team: cloud"),
            ],
            id="size above warn level -> WARN",
        ),
    ],
)
def test_check_aws_s3_objects(params: Mapping[str, object], expected: CheckResult) -> None:
    section = parse_aws_s3_bucket(_bucket_string_table(_BUCKET_VALUES))
    assert section is not None
    assert list(check_aws_s3_objects(params, section)) == expected
