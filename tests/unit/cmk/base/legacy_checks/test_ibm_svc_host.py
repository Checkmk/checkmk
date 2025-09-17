#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Mapping, Sequence
from typing import Any

import pytest

from cmk.agent_based.v1.type_defs import StringTable
from cmk.base.legacy_checks.ibm_svc_host import (
    check_ibm_svc_host,
    discover_ibm_svc_host,
    parse_ibm_svc_host,
)


@pytest.mark.parametrize(
    "string_table, expected_discoveries",
    [
        (
            [
                ["0", "h_esx01", "2", "4", "degraded"],
                ["1", "host206", "2", "2", "online"],
                ["2", "host105", "2", "2", "online"],
                ["3", "host106", "2", "2", "online"],
            ],
            [(None, {})],
        ),
    ],
)
def test_discover_ibm_svc_host(
    string_table: StringTable, expected_discoveries: Sequence[tuple[str | None, Mapping[str, Any]]]
) -> None:
    """Test discovery function for ibm_svc_host check."""
    parsed = parse_ibm_svc_host(string_table)
    result = list(discover_ibm_svc_host(parsed))
    assert sorted(result) == sorted(expected_discoveries)


@pytest.mark.parametrize(
    "item, params, string_table, expected_results",
    [
        (
            None,
            {},
            [
                ["0", "h_esx01", "2", "4", "degraded"],
                ["1", "host206", "2", "2", "online"],
                ["2", "host105", "2", "2", "online"],
                ["3", "host106", "2", "2", "online"],
            ],
            [
                (0, "3 active"),
                (0, "0 inactive", [("inactive", 0, None, None)]),
                (0, "1 degraded", [("degraded", 1, None, None)]),
                (0, "0 offline", [("offline", 0, None, None)]),
                (0, "0 other", [("other", 0, None, None)]),
            ],
        ),
    ],
)
def test_check_ibm_svc_host(
    item: str, params: Mapping[str, Any], string_table: StringTable, expected_results: Sequence[Any]
) -> None:
    """Test check function for ibm_svc_host check."""
    parsed = parse_ibm_svc_host(string_table)
    result = list(check_ibm_svc_host(item, params, parsed))
    assert result == expected_results
