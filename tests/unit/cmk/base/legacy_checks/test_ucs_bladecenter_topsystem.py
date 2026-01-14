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
from cmk.base.legacy_checks.ucs_bladecenter_topsystem import (
    check_ucs_bladecenter_topsystem,
    discover_ucs_bladecenter_topsystem,
    parse_ucs_bladecenter_topsystem,
)


@pytest.mark.parametrize(
    "string_table, expected_discoveries",
    [
        (
            [
                [
                    "topSystem",
                    "Address 192.168.1.1",
                    "CurrentTime 2015-07-15T16:40:27.600",
                    "Ipv6Addr ::",
                    "Mode cluster",
                    "Name svie23ucsfi01",
                    "SystemUpTime 125:16:10:53",
                ]
            ],
            [(None, None)],
        ),
    ],
)
def test_discover_ucs_bladecenter_topsystem(
    string_table: StringTable, expected_discoveries: Sequence[tuple[str, Mapping[str, Any]]]
) -> None:
    """Test discovery function for ucs_bladecenter_topsystem check."""
    parsed = parse_ucs_bladecenter_topsystem(string_table)
    result = list(discover_ucs_bladecenter_topsystem(parsed))
    assert sorted(result) == sorted(expected_discoveries)


@pytest.mark.parametrize(
    "item, params, string_table, expected_results",
    [
        (
            None,
            {},
            [
                [
                    "topSystem",
                    "Address 192.168.1.1",
                    "CurrentTime 2015-07-15T16:40:27.600",
                    "Ipv6Addr ::",
                    "Mode cluster",
                    "Name svie23ucsfi01",
                    "SystemUpTime 125:16:10:53",
                ]
            ],
            [
                (0, "Address: 192.168.1.1"),
                (0, "CurrentTime: 2015-07-15T16:40:27.600"),
                (0, "Ipv6Addr: ::"),
                (0, "Mode: cluster"),
                (0, "Name: svie23ucsfi01"),
                (0, "SystemUpTime: 125:16:10:53"),
            ],
        ),
    ],
)
def test_check_ucs_bladecenter_topsystem(
    item: str, params: Mapping[str, Any], string_table: StringTable, expected_results: Sequence[Any]
) -> None:
    """Test check function for ucs_bladecenter_topsystem check."""
    parsed = parse_ucs_bladecenter_topsystem(string_table)
    result = list(check_ucs_bladecenter_topsystem(item, params, parsed))
    assert result == expected_results
