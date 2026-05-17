#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Sequence

import pytest

from cmk.agent_based.v2 import Metric, Result, Service, State, StringTable
from cmk.plugins.db2.agent_based.db2_bp_hitratios import (
    check_db2_bp_hitratios,
    discover_db2_bp_hitratios,
    parse_db2_bp_hitratios,
)


@pytest.mark.parametrize(
    "string_table, expected_discoveries",
    [
        (
            [
                ["[[[serv0:ABC]]]"],
                ["node", "0", "foo1.bar2.baz3", "0"],
                [
                    "BP_NAME",
                    "TOTAL_HIT_RATIO_PERCENT",
                    "DATA_HIT_RATIO_PERCENT",
                    "INDEX_HIT_RATIO_PERCENT",
                    "XDA_HIT_RATIO_PERCENT",
                ],
                ["IBMDEFAULTBP", "83.62", "78.70", "99.74", "50.00"],
                ["[[[serv1:XYZ]]]"],
                ["node", "0", "foo1.bar2.baz3", "0"],
            ],
            [Service(item="serv0:ABC DPF 0 foo1.bar2.baz3 0:IBMDEFAULTBP")],
        ),
    ],
)
def test_discover_db2_bp_hitratios(
    string_table: StringTable, expected_discoveries: Sequence[Service]
) -> None:
    """Test discovery function for db2_bp_hitratios check."""
    parsed = parse_db2_bp_hitratios(string_table)
    result = list(discover_db2_bp_hitratios(parsed))
    assert result == list(expected_discoveries)


@pytest.mark.parametrize(
    "item, string_table, expected_results",
    [
        (
            "serv0:ABC DPF 0 foo1.bar2.baz3 0:IBMDEFAULTBP",
            [
                ["[[[serv0:ABC]]]"],
                ["node", "0", "foo1.bar2.baz3", "0"],
                [
                    "BP_NAME",
                    "TOTAL_HIT_RATIO_PERCENT",
                    "DATA_HIT_RATIO_PERCENT",
                    "INDEX_HIT_RATIO_PERCENT",
                    "XDA_HIT_RATIO_PERCENT",
                ],
                ["IBMDEFAULTBP", "83.62", "78.70", "99.74", "50.00"],
                ["[[[serv1:XYZ]]]"],
                ["node", "0", "foo1.bar2.baz3", "0"],
            ],
            [
                Result(state=State.OK, summary="Total: 83.62%"),
                Metric("total_hitratio", 83.62, boundaries=(0.0, 100.0)),
                Result(state=State.OK, summary="Data: 78.70%"),
                Metric("data_hitratio", 78.7, boundaries=(0.0, 100.0)),
                Result(state=State.OK, summary="Index: 99.74%"),
                Metric("index_hitratio", 99.74, boundaries=(0.0, 100.0)),
                Result(state=State.OK, summary="XDA: 50.00%"),
                Metric("xda_hitratio", 50.0, boundaries=(0.0, 100.0)),
            ],
        ),
    ],
)
def test_check_db2_bp_hitratios(
    item: str, string_table: StringTable, expected_results: Sequence[Result | Metric]
) -> None:
    """Test check function for db2_bp_hitratios check."""
    parsed = parse_db2_bp_hitratios(string_table)
    result = list(check_db2_bp_hitratios(item, parsed))
    assert result == list(expected_results)
