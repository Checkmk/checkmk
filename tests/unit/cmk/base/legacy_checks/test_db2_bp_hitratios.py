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
from cmk.base.legacy_checks.db2_bp_hitratios import (
    check_db2_bp_hitratios,
    inventory_db2_bp_hitratios,
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
            [("serv0:ABC DPF 0 foo1.bar2.baz3 0:IBMDEFAULTBP", {})],
        ),
    ],
)
def test_inventory_db2_bp_hitratios(
    string_table: StringTable, expected_discoveries: Sequence[tuple[str, Mapping[str, Any]]]
) -> None:
    """Test discovery function for db2_bp_hitratios check."""
    parsed = parse_db2_bp_hitratios(string_table)
    result = list(inventory_db2_bp_hitratios(parsed))
    assert sorted(result) == sorted(expected_discoveries)


@pytest.mark.parametrize(
    "item, params, string_table, expected_results",
    [
        (
            "serv0:ABC DPF 0 foo1.bar2.baz3 0:IBMDEFAULTBP",
            {},
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
                (0, "Total: 83.62%", [("total_hitratio", 83.62, None, None, 0, 100)]),
                (0, "Data: 78.70%", [("data_hitratio", 78.7, None, None, 0, 100)]),
                (0, "Index: 99.74%", [("index_hitratio", 99.74, None, None, 0, 100)]),
                (0, "XDA: 50.00%", [("xda_hitratio", 50.0, None, None, 0, 100)]),
            ],
        ),
    ],
)
def test_check_db2_bp_hitratios(
    item: str, params: Mapping[str, Any], string_table: StringTable, expected_results: Sequence[Any]
) -> None:
    """Test check function for db2_bp_hitratios check."""
    parsed = parse_db2_bp_hitratios(string_table)
    result = list(check_db2_bp_hitratios(item, params, parsed))
    assert result == expected_results


# Crash group 4696: DB2 answered with an error message instead of the hit ratio table
_STRING_TABLE_SQL_ERROR: StringTable = [
    ["[[[db2inst1:DEVRU]]]"],
    [
        "SQL20249N",
        "The",
        "statement",
        "was",
        "not",
        "processed",
        "because",
        "the",
        "package",
        "named",
    ],
    ['"NULLID.SQLC2P31"', "needs", "to", "be", "explicitly", "rebound."],
]


@pytest.mark.xfail(
    strict=True,
    raises=AssertionError,
    reason="Crash group 4696: SQL error message is discovered as a buffer pool",
)
def test_inventory_db2_bp_hitratios_sql_error() -> None:
    parsed = parse_db2_bp_hitratios(_STRING_TABLE_SQL_ERROR)
    assert not list(inventory_db2_bp_hitratios(parsed))


@pytest.mark.xfail(strict=True, raises=KeyError, reason="Crash group 4696: KeyError")
def test_check_db2_bp_hitratios_sql_error() -> None:
    parsed = parse_db2_bp_hitratios(_STRING_TABLE_SQL_ERROR)
    assert list(check_db2_bp_hitratios('db2inst1:DEVRU:"NULLID.SQLC2P31"', {}, parsed)) == [
        (
            3,
            "Cannot read buffer pool hit ratios: SQL20249N The statement was not"
            ' processed because the package named "NULLID.SQLC2P31" needs to be'
            " explicitly rebound.",
        ),
    ]
