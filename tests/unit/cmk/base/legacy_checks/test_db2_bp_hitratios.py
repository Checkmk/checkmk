#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# mypy: disable-error-code="no-untyped-call"

from cmk.base.legacy_checks.db2_bp_hitratios import (
    check_db2_bp_hitratios,
    inventory_db2_bp_hitratios,
    parse_db2_bp_hitratios,
)

from cmk.agent_based.v2 import StringTable

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


def test_inventory_db2_bp_hitratios_sql_error() -> None:
    parsed = parse_db2_bp_hitratios(_STRING_TABLE_SQL_ERROR)
    assert not list(inventory_db2_bp_hitratios(parsed))


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
