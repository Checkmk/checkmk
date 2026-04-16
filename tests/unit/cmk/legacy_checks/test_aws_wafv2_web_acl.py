#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# mypy: disable-error-code="misc"

from collections.abc import Mapping, Sequence
from typing import Any

import pytest

from cmk.agent_based.v2 import Metric, Result, Service, State, StringTable
from cmk.legacy_checks.aws_wafv2_web_acl import (
    check_aws_wafv2_web_acl,
    discover_aws_wafv2_web_acl,
    parse_aws_wafv2_web_acl,
)

_STRING_TABLE: StringTable = [
    [
        '[{"Id":',
        '"id_0_AllowedRequests",',
        '"Label":',
        '"joerg-herbel-acl_eu-central-1",',
        '"Timestamps":',
        '["2020-04-28',
        '08:45:00+00:00"],',
        '"Values":',
        "[[11.0,",
        "600]],",
        '"StatusCode":',
        '"Complete"},',
        '{"Id":',
        '"id_0_BlockedRequests",',
        '"Label":',
        '"joerg-herbel-acl_eu-central-1",',
        '"Timestamps":',
        '["2020-04-28',
        '08:45:00+00:00"],',
        '"Values":',
        "[[9.0,",
        "600]],",
        '"StatusCode":',
        '"Complete"}]',
    ]
]


@pytest.mark.parametrize(
    "string_table, expected_discoveries",
    [
        (_STRING_TABLE, [Service()]),
    ],
)
def test_discover_aws_wafv2_web_acl(
    string_table: StringTable, expected_discoveries: Sequence[Service]
) -> None:
    """Test discovery function for aws_wafv2_web_acl check."""
    parsed = parse_aws_wafv2_web_acl(string_table)
    result = list(discover_aws_wafv2_web_acl(parsed))
    assert result == expected_discoveries


@pytest.mark.parametrize(
    "params, string_table, expected_results",
    [
        (
            {"allowed_requests_perc": (10.0, 20.0), "blocked_requests_perc": (10.0, 20.0)},
            _STRING_TABLE,
            [
                Result(state=State.OK, summary="Total requests: 0.033/s"),
                Metric("aws_wafv2_requests_rate", 0.03333333333333333),
                Result(state=State.OK, summary="Allowed requests: 0.018/s"),
                Metric("aws_wafv2_allowed_requests_rate", 0.018333333333333333),
                Result(
                    state=State.CRIT,
                    summary="Percentage allowed requests: 55.00% (warn/crit at 10.00%/20.00%)",
                ),
                Metric("aws_wafv2_allowed_requests_perc", 55.0, levels=(10.0, 20.0)),
                Result(state=State.OK, summary="Blocked requests: 0.015/s"),
                Metric("aws_wafv2_blocked_requests_rate", 0.015),
                Result(
                    state=State.CRIT,
                    summary="Percentage blocked requests: 45.00% (warn/crit at 10.00%/20.00%)",
                ),
                Metric("aws_wafv2_blocked_requests_perc", 45.0, levels=(10.0, 20.0)),
            ],
        ),
    ],
)
def test_check_aws_wafv2_web_acl(
    params: Mapping[str, Any], string_table: StringTable, expected_results: Sequence[Any]
) -> None:
    """Test check function for aws_wafv2_web_acl check."""
    parsed = parse_aws_wafv2_web_acl(string_table)
    result = list(check_aws_wafv2_web_acl(params, parsed))
    assert result == expected_results
