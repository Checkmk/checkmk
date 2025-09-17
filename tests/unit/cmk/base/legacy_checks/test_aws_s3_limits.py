#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Mapping, Sequence
from typing import Any

import pytest

from cmk.agent_based.v1.type_defs import StringTable
from cmk.base.check_legacy_includes.aws import parse_aws_limits_generic
from cmk.base.legacy_checks.aws_s3_limits import check_aws_s3_limits, discover_aws_s3_limits


@pytest.mark.parametrize(
    "info, expected_discoveries",
    [
        ([['[["buckets",', '"TITLE",', "10,", "1,", '"REGION"]]']], [("REGION", {})]),
    ],
)
def test_discover_aws_s3_limits(
    info: StringTable, expected_discoveries: Sequence[tuple[str, Mapping[str, Any]]]
) -> None:
    """Test discovery function for aws_s3_limits check."""
    parsed = parse_aws_limits_generic(info)
    result = list(discover_aws_s3_limits(parsed))
    assert sorted(result) == sorted(expected_discoveries)


@pytest.mark.parametrize(
    "item, params, info, expected_results",
    [
        (
            "REGION",
            {"buckets": (None, 80.0, 90.0)},
            [['[["buckets",', '"TITLE",', "10,", "1,", '"REGION"]]']],
            [
                (0, "No levels reached", [("aws_s3_buckets", 1)]),
                (0, "\nTITLE: 1 (of max. 10)"),
            ],
        ),
    ],
)
def test_check_aws_s3_limits(
    item: str, params: Mapping[str, Any], info: StringTable, expected_results: Sequence[Any]
) -> None:
    """Test check function for aws_s3_limits check."""
    parsed = parse_aws_limits_generic(info)
    result = list(check_aws_s3_limits(item, params, parsed))
    assert result == expected_results
