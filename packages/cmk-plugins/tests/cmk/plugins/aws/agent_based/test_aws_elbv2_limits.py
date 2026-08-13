#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# mypy: disable-error-code="explicit-any"

from collections.abc import Mapping, Sequence
from typing import Any

import pytest

from cmk.agent_based.v2 import Metric, Result, Service, State, StringTable
from cmk.plugins.aws.agent_based.aws_elbv2_limits import (
    check_aws_elbv2_limits,
    discover_aws_elbv2_limits,
)
from cmk.plugins.aws.lib import parse_aws_limits_generic


@pytest.mark.parametrize(
    "info, expected_discoveries",
    [
        (
            [['[["application_load_balancers",', '"TITLE",', "10,", "1,", '"REGION"]]']],
            [Service(item="REGION")],
        ),
    ],
)
def test_discover_aws_elbv2_limits(
    info: StringTable, expected_discoveries: Sequence[Service]
) -> None:
    """Test discovery function for aws_elbv2_limits check."""

    parsed_section = parse_aws_limits_generic(info)
    assert list(discover_aws_elbv2_limits(parsed_section)) == list(expected_discoveries)


@pytest.mark.parametrize(
    "item, params, info, expected_results",
    [
        (
            "REGION",
            {
                "application_load_balancer_target_groups": (None, 80.0, 90.0),
                "application_load_balancer_certificates": (None, 80.0, 90.0),
                "application_load_balancer_rules": (None, 80.0, 90.0),
                "network_load_balancers": (None, 80.0, 90.0),
                "load_balancer_target_groups": (None, 80.0, 90.0),
                "application_load_balancers": (None, 80.0, 90.0),
                "network_load_balancer_target_groups": (None, 80.0, 90.0),
                "application_load_balancer_listeners": (None, 80.0, 90.0),
                "network_load_balancer_listeners": (None, 80.0, 90.0),
            },
            [['[["application_load_balancers",', '"TITLE",', "10,", "1,", '"REGION"]]']],
            [
                Metric("aws_elbv2_application_load_balancers", 1.0),
                Result(state=State.OK, notice="TITLE: 1 (of max. 10), 10.00%"),
            ],
        ),
    ],
)
def test_check_aws_elbv2_limits(  # type: ignore[misc]
    item: str,
    params: Mapping[str, Any],
    info: StringTable,
    expected_results: Sequence[Metric | Result],
) -> None:
    """Test check function for aws_elbv2_limits check."""

    parsed_section = parse_aws_limits_generic(info)
    assert list(check_aws_elbv2_limits(item, params, parsed_section)) == list(expected_results)
