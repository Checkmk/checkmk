#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# mypy: disable-error-code="misc"
# mypy: disable-error-code="no-untyped-call"

from collections.abc import Mapping, Sequence
from typing import Any

import pytest

from cmk.agent_based.v2 import StringTable
from cmk.base.check_legacy_includes.aws import parse_aws_limits_generic
from cmk.base.legacy_checks.aws_elb_limits import check_aws_elb_limits, discover_aws_elb_limits


@pytest.mark.parametrize(
    "info, expected_discoveries",
    [
        ([['[["load_balancers",', '"TITLE",', "10,", "1,", '"REGION"]]']], [("REGION", {})]),
    ],
)
def test_discover_aws_elb_limits(
    info: StringTable, expected_discoveries: Sequence[tuple[str, Mapping[str, Any]]]
) -> None:
    """Test discovery function for aws_elb_limits check."""

    parsed_section = parse_aws_limits_generic(info)
    result = list(discover_aws_elb_limits(parsed_section))
    assert sorted(result) == sorted(expected_discoveries)


@pytest.mark.parametrize(
    "item, params, info, expected_results",
    [
        (
            "REGION",
            {
                "load_balancer_registered_instances": (None, 80.0, 90.0),
                "load_balancer_listeners": (None, 80.0, 90.0),
                "load_balancers": (None, 80.0, 90.0),
            },
            [['[["load_balancers",', '"TITLE",', "10,", "1,", '"REGION"]]']],
            [
                (0, "No levels reached", [("aws_elb_load_balancers", 1)]),
                (0, "\nTITLE: 1 (of max. 10)"),
            ],
        ),
    ],
)
def test_check_aws_elb_limits(
    item: str, params: Mapping[str, Any], info: StringTable, expected_results: Sequence[Any]
) -> None:
    """Test check function for aws_elb_limits check."""

    parsed_section = parse_aws_limits_generic(info)
    result = list(check_aws_elb_limits(item, params, parsed_section))
    assert result == expected_results
