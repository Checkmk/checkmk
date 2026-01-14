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
from cmk.base.legacy_checks.ucs_c_rack_server_topsystem import (
    check_ucs_c_rack_server_topsystem,
    discover_ucs_c_rack_server_topsystem,
    parse_ucs_c_rack_server_topsystem,
)


@pytest.mark.parametrize(
    "string_table, expected_discoveries",
    [
        (
            [
                [
                    "topSystem",
                    "dn sys",
                    "address 192.168.1.1",
                    "currentTime Wed Feb  6 09:12:12 2019",
                    "mode stand-alone",
                    "name CIMC-istreamer2a-etn",
                ]
            ],
            [(None, None)],
        ),
    ],
)
def test_discover_ucs_c_rack_server_topsystem(
    string_table: StringTable, expected_discoveries: Sequence[tuple[str, Mapping[str, Any]]]
) -> None:
    """Test discovery function for ucs_c_rack_server_topsystem check."""
    parsed = parse_ucs_c_rack_server_topsystem(string_table)
    result = list(discover_ucs_c_rack_server_topsystem(parsed))
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
                    "dn sys",
                    "address 192.168.1.1",
                    "currentTime Wed Feb  6 09:12:12 2019",
                    "mode stand-alone",
                    "name CIMC-istreamer2a-etn",
                ]
            ],
            [
                (0, "DN: sys"),
                (0, "IP: 192.168.1.1"),
                (0, "Mode: stand-alone"),
                (0, "Name: CIMC-istreamer2a-etn"),
                (0, "Date and time: 2019-02-06 09:12:12"),
            ],
        ),
    ],
)
def test_check_ucs_c_rack_server_topsystem(
    item: str, params: Mapping[str, Any], string_table: StringTable, expected_results: Sequence[Any]
) -> None:
    """Test check function for ucs_c_rack_server_topsystem check."""
    parsed = parse_ucs_c_rack_server_topsystem(string_table)
    result = list(check_ucs_c_rack_server_topsystem(item, params, parsed))
    assert result == expected_results
