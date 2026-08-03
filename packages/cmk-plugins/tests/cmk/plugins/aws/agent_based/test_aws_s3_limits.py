#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# mypy: disable-error-code="explicit-any"
# mypy: disable-error-code="misc"

from collections.abc import Mapping, Sequence
from typing import Any

import pytest

from cmk.agent_based.v2 import Metric, Result, Service, State, StringTable
from cmk.plugins.aws.agent_based.aws_s3_limits import check_aws_s3_limits, discover_aws_s3_limits
from cmk.plugins.aws.lib import parse_aws_limits_generic


@pytest.mark.parametrize(
    "info, expected_discoveries",
    [
        ([['[["buckets",', '"TITLE",', "10,", "1,", '"REGION"]]']], [Service(item="REGION")]),
    ],
)
def test_discover_aws_s3_limits(info: StringTable, expected_discoveries: Sequence[Service]) -> None:
    """Test discovery function for aws_s3_limits check."""
    parsed = parse_aws_limits_generic(info)
    assert list(discover_aws_s3_limits(parsed)) == list(expected_discoveries)


@pytest.mark.parametrize(
    "item, params, info, expected_results",
    [
        (
            "REGION",
            {"buckets": (None, 80.0, 90.0)},
            [['[["buckets",', '"TITLE",', "10,", "1,", '"REGION"]]']],
            [
                Metric("aws_s3_buckets", 1.0),
                Result(state=State.OK, notice="TITLE: 1 (of max. 10), 10.00%"),
            ],
        ),
    ],
)
def test_check_aws_s3_limits(
    item: str,
    params: Mapping[str, Any],
    info: StringTable,
    expected_results: Sequence[Metric | Result],
) -> None:
    """Test check function for aws_s3_limits check."""
    parsed = parse_aws_limits_generic(info)
    assert list(check_aws_s3_limits(item, params, parsed)) == list(expected_results)
