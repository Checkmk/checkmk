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
from cmk.base.legacy_checks.ucs_c_rack_server_fans import (
    check_ucs_c_rack_server_fans,
    discover_ucs_c_rack_server_fans,
    parse_ucs_c_rack_server_fans,
)


@pytest.mark.parametrize(
    "string_table, expected_discoveries",
    [
        (
            [
                [
                    "equipmentFan",
                    "dn sys/rack-unit-1/fan-module-1-1/fan-1",
                    "id 1",
                    "model ",
                    "operability operable",
                ],
                [
                    "equipmentFan",
                    "dn sys/rack-unit-1/fan-module-1-1/fan-2",
                    "id 2",
                    "model ",
                    "operability operable",
                ],
                [
                    "equipmentFan",
                    "dn sys/rack-unit-2/fan-module-1-1/fan-1",
                    "id 1",
                    "model ",
                    "operability operable",
                ],
                [
                    "equipmentFan",
                    "dn sys/rack-unit-2/fan-module-1-1/fan-2",
                    "id 2",
                    "model ",
                    "operability bla",
                ],
                [
                    "equipmentFan",
                    "dn sys/rack-unit-2/fan-module-1-1/fan-3",
                    "id 3",
                    "model ",
                    "operability blub",
                ],
            ],
            [
                ("Rack Unit 1 Module 1-1 1", {}),
                ("Rack Unit 1 Module 1-1 2", {}),
                ("Rack Unit 2 Module 1-1 1", {}),
                ("Rack Unit 2 Module 1-1 2", {}),
                ("Rack Unit 2 Module 1-1 3", {}),
            ],
        ),
    ],
)
def test_discover_ucs_c_rack_server_fans(
    string_table: StringTable, expected_discoveries: Sequence[tuple[str, Mapping[str, Any]]]
) -> None:
    """Test discovery function for ucs_c_rack_server_fans check."""
    parsed = parse_ucs_c_rack_server_fans(string_table)
    result = list(discover_ucs_c_rack_server_fans(parsed))
    assert sorted(result) == sorted(expected_discoveries)


@pytest.mark.parametrize(
    "item, params, string_table, expected_results",
    [
        (
            "Rack Unit 1 Module 1-1 1",
            {},
            [
                [
                    "equipmentFan",
                    "dn sys/rack-unit-1/fan-module-1-1/fan-1",
                    "id 1",
                    "model ",
                    "operability operable",
                ],
                [
                    "equipmentFan",
                    "dn sys/rack-unit-1/fan-module-1-1/fan-2",
                    "id 2",
                    "model ",
                    "operability operable",
                ],
                [
                    "equipmentFan",
                    "dn sys/rack-unit-2/fan-module-1-1/fan-1",
                    "id 1",
                    "model ",
                    "operability operable",
                ],
                [
                    "equipmentFan",
                    "dn sys/rack-unit-2/fan-module-1-1/fan-2",
                    "id 2",
                    "model ",
                    "operability bla",
                ],
                [
                    "equipmentFan",
                    "dn sys/rack-unit-2/fan-module-1-1/fan-3",
                    "id 3",
                    "model ",
                    "operability blub",
                ],
            ],
            [(0, "Operability Status is operable")],
        ),
        (
            "Rack Unit 1 Module 1-1 2",
            {},
            [
                [
                    "equipmentFan",
                    "dn sys/rack-unit-1/fan-module-1-1/fan-1",
                    "id 1",
                    "model ",
                    "operability operable",
                ],
                [
                    "equipmentFan",
                    "dn sys/rack-unit-1/fan-module-1-1/fan-2",
                    "id 2",
                    "model ",
                    "operability operable",
                ],
                [
                    "equipmentFan",
                    "dn sys/rack-unit-2/fan-module-1-1/fan-1",
                    "id 1",
                    "model ",
                    "operability operable",
                ],
                [
                    "equipmentFan",
                    "dn sys/rack-unit-2/fan-module-1-1/fan-2",
                    "id 2",
                    "model ",
                    "operability bla",
                ],
                [
                    "equipmentFan",
                    "dn sys/rack-unit-2/fan-module-1-1/fan-3",
                    "id 3",
                    "model ",
                    "operability blub",
                ],
            ],
            [(0, "Operability Status is operable")],
        ),
        (
            "Rack Unit 2 Module 1-1 1",
            {},
            [
                [
                    "equipmentFan",
                    "dn sys/rack-unit-1/fan-module-1-1/fan-1",
                    "id 1",
                    "model ",
                    "operability operable",
                ],
                [
                    "equipmentFan",
                    "dn sys/rack-unit-1/fan-module-1-1/fan-2",
                    "id 2",
                    "model ",
                    "operability operable",
                ],
                [
                    "equipmentFan",
                    "dn sys/rack-unit-2/fan-module-1-1/fan-1",
                    "id 1",
                    "model ",
                    "operability operable",
                ],
                [
                    "equipmentFan",
                    "dn sys/rack-unit-2/fan-module-1-1/fan-2",
                    "id 2",
                    "model ",
                    "operability bla",
                ],
                [
                    "equipmentFan",
                    "dn sys/rack-unit-2/fan-module-1-1/fan-3",
                    "id 3",
                    "model ",
                    "operability blub",
                ],
            ],
            [(0, "Operability Status is operable")],
        ),
        (
            "Rack Unit 2 Module 1-1 2",
            {},
            [
                [
                    "equipmentFan",
                    "dn sys/rack-unit-1/fan-module-1-1/fan-1",
                    "id 1",
                    "model ",
                    "operability operable",
                ],
                [
                    "equipmentFan",
                    "dn sys/rack-unit-1/fan-module-1-1/fan-2",
                    "id 2",
                    "model ",
                    "operability operable",
                ],
                [
                    "equipmentFan",
                    "dn sys/rack-unit-2/fan-module-1-1/fan-1",
                    "id 1",
                    "model ",
                    "operability operable",
                ],
                [
                    "equipmentFan",
                    "dn sys/rack-unit-2/fan-module-1-1/fan-2",
                    "id 2",
                    "model ",
                    "operability bla",
                ],
                [
                    "equipmentFan",
                    "dn sys/rack-unit-2/fan-module-1-1/fan-3",
                    "id 3",
                    "model ",
                    "operability blub",
                ],
            ],
            [(3, "Unknown Operability Status: bla")],
        ),
        (
            "Rack Unit 2 Module 1-1 3",
            {},
            [
                [
                    "equipmentFan",
                    "dn sys/rack-unit-1/fan-module-1-1/fan-1",
                    "id 1",
                    "model ",
                    "operability operable",
                ],
                [
                    "equipmentFan",
                    "dn sys/rack-unit-1/fan-module-1-1/fan-2",
                    "id 2",
                    "model ",
                    "operability operable",
                ],
                [
                    "equipmentFan",
                    "dn sys/rack-unit-2/fan-module-1-1/fan-1",
                    "id 1",
                    "model ",
                    "operability operable",
                ],
                [
                    "equipmentFan",
                    "dn sys/rack-unit-2/fan-module-1-1/fan-2",
                    "id 2",
                    "model ",
                    "operability bla",
                ],
                [
                    "equipmentFan",
                    "dn sys/rack-unit-2/fan-module-1-1/fan-3",
                    "id 3",
                    "model ",
                    "operability blub",
                ],
            ],
            [(3, "Unknown Operability Status: blub")],
        ),
    ],
)
def test_check_ucs_c_rack_server_fans(
    item: str, params: Mapping[str, Any], string_table: StringTable, expected_results: Sequence[Any]
) -> None:
    """Test check function for ucs_c_rack_server_fans check."""
    parsed = parse_ucs_c_rack_server_fans(string_table)
    result = list(check_ucs_c_rack_server_fans(item, params, parsed))
    assert result == expected_results
