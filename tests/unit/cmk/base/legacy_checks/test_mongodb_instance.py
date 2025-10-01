#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# mypy: disable-error-code="no-untyped-call"

from collections.abc import Mapping, Sequence
from typing import Any

import pytest

from cmk.agent_based.v1.type_defs import StringTable
from cmk.agent_based.v2 import Result, Service, State
from cmk.base.legacy_checks.mongodb_instance import (
    check_mongodb_instance,
    inventory_mongodb_instance,
    parse_mongodb_instance,
)


@pytest.mark.parametrize(
    "string_table, expected_discoveries",
    [
        (
            [
                ["mode", "Primary"],
                ["address", "idbv0068.ww-intern.de:27017"],
                ["version", "3.0.4"],
                ["pid", "1999"],
            ],
            [Service()],
        ),
    ],
)
def test_inventory_mongodb_instance(
    string_table: StringTable, expected_discoveries: Sequence[Service]
) -> None:
    """Test discovery function for mongodb_instance check."""
    parsed = parse_mongodb_instance(string_table)
    assert list(inventory_mongodb_instance(parsed)) == expected_discoveries


@pytest.mark.parametrize(
    "item, params, string_table, expected_results",
    [
        (
            None,
            {},
            [
                ["mode", "Primary"],
                ["address", "idbv0068.ww-intern.de:27017"],
                ["version", "3.0.4"],
                ["pid", "1999"],
            ],
            [
                Result(state=State.OK, summary="Mode: Primary"),
                Result(state=State.OK, summary="Address: idbv0068.ww-intern.de:27017"),
                Result(state=State.OK, summary="Version: 3.0.4"),
                Result(state=State.OK, summary="Pid: 1999"),
            ],
        ),
    ],
)
def test_check_mongodb_instance(
    item: str, params: Mapping[str, Any], string_table: StringTable, expected_results: Sequence[Any]
) -> None:
    """Test check function for mongodb_instance check."""
    parsed = parse_mongodb_instance(string_table)
    result = list(check_mongodb_instance(parsed))
    assert result == expected_results
