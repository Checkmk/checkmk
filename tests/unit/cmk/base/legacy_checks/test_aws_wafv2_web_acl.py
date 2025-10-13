#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# mypy: disable-error-code="misc"
# mypy: disable-error-code="no-untyped-call"

from collections.abc import Mapping, Sequence
from typing import Any

import pytest

from cmk.agent_based.v1.type_defs import StringTable
from cmk.base.legacy_checks.aws_wafv2_web_acl import (
    check_aws_wafv2_web_acl,
    discover_aws_wafv2_web_acl,
    parse_aws_wafv2_web_acl,
)


@pytest.mark.parametrize(
    "string_table, expected_discoveries",
    [
        (
            [
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
            ],
            [(None, {})],
        ),
    ],
)
def test_discover_aws_wafv2_web_acl(
    string_table: StringTable, expected_discoveries: Sequence[tuple[str, Mapping[str, Any]]]
) -> None:
    """Test discovery function for aws_wafv2_web_acl check."""
    parsed = parse_aws_wafv2_web_acl(string_table)
    result = list(discover_aws_wafv2_web_acl(parsed))
    assert sorted(result) == sorted(expected_discoveries)


@pytest.mark.parametrize(
    "item, params, string_table, expected_results",
    [
        (
            None,
            {"allowed_requests_perc": (10.0, 20.0), "blocked_requests_perc": (10.0, 20.0)},
            [
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
            ],
            [
                (
                    0,
                    "Total requests: 0.033/s",
                    [("aws_wafv2_requests_rate", 0.03333333333333333, None, None)],
                ),
                (
                    0,
                    "Allowed requests: 0.018/s",
                    [("aws_wafv2_allowed_requests_rate", 0.018333333333333333, None, None)],
                ),
                (
                    2,
                    "Percentage allowed requests: 55.00% (warn/crit at 10.00%/20.00%)",
                    [("aws_wafv2_allowed_requests_perc", 55.0, 10.0, 20.0)],
                ),
                (
                    0,
                    "Blocked requests: 0.015/s",
                    [("aws_wafv2_blocked_requests_rate", 0.015, None, None)],
                ),
                (
                    2,
                    "Percentage blocked requests: 45.00% (warn/crit at 10.00%/20.00%)",
                    [("aws_wafv2_blocked_requests_perc", 45.0, 10.0, 20.0)],
                ),
            ],
        ),
    ],
)
def test_check_aws_wafv2_web_acl(
    item: str, params: Mapping[str, Any], string_table: StringTable, expected_results: Sequence[Any]
) -> None:
    """Test check function for aws_wafv2_web_acl check."""
    parsed = parse_aws_wafv2_web_acl(string_table)
    result = list(check_aws_wafv2_web_acl(item, params, parsed))
    assert result == expected_results
