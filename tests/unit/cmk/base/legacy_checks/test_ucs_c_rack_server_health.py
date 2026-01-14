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
from cmk.base.legacy_checks.ucs_c_rack_server_health import (
    check_ucs_c_rack_server_health,
    discover_ucs_c_rack_server_health,
    parse_ucs_c_rack_server_health,
)


@pytest.mark.parametrize(
    "string_table, expected_discoveries",
    [
        (
            [
                [
                    "storageControllerHealth",
                    "dn sys/rack-unit-1/board/storage-SAS-SLOT-HBA/vd-0",
                    "id SLOT-HBA",
                    "health Good",
                ],
                [
                    "storageControllerHealth",
                    "dn sys/rack-unit-2/board/storage-SAS-SLOT-HBA/vd-0",
                    "id SLOT-HBA",
                    "health AnythingElse",
                ],
            ],
            [
                ("Rack unit 1 Storage SAS SLOT HBA vd 0", {}),
                ("Rack unit 2 Storage SAS SLOT HBA vd 0", {}),
            ],
        ),
    ],
)
def test_discover_ucs_c_rack_server_health(
    string_table: StringTable, expected_discoveries: Sequence[tuple[str, Mapping[str, Any]]]
) -> None:
    """Test discovery function for ucs_c_rack_server_health check."""
    parsed = parse_ucs_c_rack_server_health(string_table)
    result = list(discover_ucs_c_rack_server_health(parsed))
    assert sorted(result) == sorted(expected_discoveries)


@pytest.mark.parametrize(
    "item, params, string_table, expected_results",
    [
        (
            "Rack unit 1 Storage SAS SLOT HBA vd 0",
            {},
            [
                [
                    "storageControllerHealth",
                    "dn sys/rack-unit-1/board/storage-SAS-SLOT-HBA/vd-0",
                    "id SLOT-HBA",
                    "health Good",
                ],
                [
                    "storageControllerHealth",
                    "dn sys/rack-unit-2/board/storage-SAS-SLOT-HBA/vd-0",
                    "id SLOT-HBA",
                    "health AnythingElse",
                ],
            ],
            [(0, "Status: good")],
        ),
        (
            "Rack unit 2 Storage SAS SLOT HBA vd 0",
            {},
            [
                [
                    "storageControllerHealth",
                    "dn sys/rack-unit-1/board/storage-SAS-SLOT-HBA/vd-0",
                    "id SLOT-HBA",
                    "health Good",
                ],
                [
                    "storageControllerHealth",
                    "dn sys/rack-unit-2/board/storage-SAS-SLOT-HBA/vd-0",
                    "id SLOT-HBA",
                    "health AnythingElse",
                ],
            ],
            [(3, "Status: unknown[anythingelse]")],
        ),
    ],
)
def test_check_ucs_c_rack_server_health(
    item: str, params: Mapping[str, Any], string_table: StringTable, expected_results: Sequence[Any]
) -> None:
    """Test check function for ucs_c_rack_server_health check."""
    parsed = parse_ucs_c_rack_server_health(string_table)
    result = list(check_ucs_c_rack_server_health(item, params, parsed))
    assert result == expected_results
