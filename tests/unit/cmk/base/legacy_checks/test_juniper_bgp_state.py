#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# NOTE: This file has been created by an LLM (from something that was worse).
# It mostly serves as test to ensure we don't accidentally break anything.
# If you encounter something weird in here, do not hesitate to replace this
# test by something more appropriate.

from collections.abc import Mapping, Sequence
from typing import Any

import pytest

from cmk.agent_based.v1.type_defs import StringTable
from cmk.base.legacy_checks.juniper_bgp_state import (
    check_juniper_bgp_state,
    discover_juniper_bgp_state,
    parse_juniper_bgp_state,
)


@pytest.mark.parametrize(
    "string_table, expected_discoveries",
    [
        (
            [["6", "2", [100, 96, 1, 34]], ["3", "2", [100, 96, 1, 38]]],
            [("100.96.1.34", {}), ("100.96.1.38", {})],
        ),
        (
            [
                [
                    "4",
                    "1",
                    [
                        "222",
                        "173",
                        "190",
                        "239",
                        "0",
                        "64",
                        "1",
                        "17",
                        "0",
                        "0",
                        "0",
                        "0",
                        "0",
                        "0",
                        "0",
                        "1",
                    ],
                ],
                ["4", "2", ["0"] * 16],
            ],
            [("[dead:beef:40:111::1]", {}), ("[::]", {})],
        ),
    ],
)
def test_discover_juniper_bgp_state(
    string_table: StringTable, expected_discoveries: Sequence[tuple[str, Mapping[str, Any]]]
) -> None:
    """Test discovery function for juniper_bgp_state check."""
    parsed = parse_juniper_bgp_state(string_table)
    result = list(discover_juniper_bgp_state(parsed))
    assert sorted(result) == sorted(expected_discoveries)


@pytest.mark.parametrize(
    "item, params, string_table, expected_results",
    [
        (
            "100.96.1.34",
            {},
            [["6", "2", [100, 96, 1, 34]], ["3", "2", [100, 96, 1, 38]]],
            [
                (0, "Status with peer 100.96.1.34 is established"),
                (0, "operational status: running"),
            ],
        ),
        (
            "100.96.1.38",
            {},
            [["6", "2", [100, 96, 1, 34]], ["3", "2", [100, 96, 1, 38]]],
            [(2, "Status with peer 100.96.1.38 is active"), (0, "operational status: running")],
        ),
        (
            "[dead:beef:40:111::1]",
            {},
            [
                [
                    "4",
                    "1",
                    [
                        "222",
                        "173",
                        "190",
                        "239",
                        "0",
                        "64",
                        "1",
                        "17",
                        "0",
                        "0",
                        "0",
                        "0",
                        "0",
                        "0",
                        "0",
                        "1",
                    ],
                ],
                ["4", "2", ["0"] * 16],
            ],
            [
                (0, "Status with peer [dead:beef:40:111::1] is opensent"),
                (1, "operational status: halted"),
            ],
        ),
        (
            "[::]",
            {},
            [
                [
                    "4",
                    "1",
                    [
                        "222",
                        "173",
                        "190",
                        "239",
                        "0",
                        "64",
                        "1",
                        "17",
                        "0",
                        "0",
                        "0",
                        "0",
                        "0",
                        "0",
                        "0",
                        "1",
                    ],
                ],
                ["4", "2", ["0"] * 16],
            ],
            [
                (2, "Status with peer [::] is opensent"),
                (0, "operational status: running"),
            ],
        ),
    ],
)
def test_check_juniper_bgp_state(
    item: str, params: Mapping[str, Any], string_table: StringTable, expected_results: Sequence[Any]
) -> None:
    """Test check function for juniper_bgp_state check."""
    parsed = parse_juniper_bgp_state(string_table)
    result = list(check_juniper_bgp_state(item, params, parsed))
    assert result == expected_results
