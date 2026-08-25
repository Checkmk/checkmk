#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


from collections.abc import Sequence

import pytest

from cmk.agent_based.v2 import (
    CheckResult,
    InventoryResult,
    Metric,
    Result,
    Service,
    State,
    StringTable,
    TableRow,
)
from cmk.plugins.oracle.agent_based.oracle_recovery_area import (
    check_plugin_oracle_recovery_area,
    inventory_oracle_recovery_area,
    parse_oracle_recovery_area,
)

_AGENT_OUTPUT = [
    ["AIMDWHD1", "300", "51235", "49000", "300"],
]


def test_discover_oracle_recovery_area_skips_failure_row() -> None:
    assert not list(
        check_plugin_oracle_recovery_area.discovery_function(
            parse_oracle_recovery_area(
                [
                    ["AIMDWHD1", "FAILURE", "ORA-00942: table or view does not exist"],
                ]
            )
        )
    )


def test_check_oracle_recovery_area_surfaces_failure() -> None:
    assert list(
        check_plugin_oracle_recovery_area.check_function(
            item="AIMDWHD1",
            params={"levels": (70.0, 90.0)},
            section=parse_oracle_recovery_area(
                [
                    ["AIMDWHD1", "FAILURE", "ORA-00942: table or view does not exist"],
                ]
            ),
        )
    ) == [Result(state=State.UNKNOWN, summary="ORA-00942: table or view does not exist")]


def test_inventory_oracle_recovery_area_skips_failure_row() -> None:
    assert not list(
        inventory_oracle_recovery_area(
            parse_oracle_recovery_area(
                [
                    ["AIMDWHD1", "FAILURE", "ORA-00942: table or view does not exist"],
                ]
            )
        )
    )


@pytest.mark.parametrize(
    "string_table, expected_result",
    [
        (
            _AGENT_OUTPUT,
            [
                Service(item="AIMDWHD1"),
            ],
        ),
    ],
)
def test_discover_oracle_recovery_area(
    string_table: StringTable,
    expected_result: Sequence[Service],
) -> None:
    assert (
        sorted(
            check_plugin_oracle_recovery_area.discovery_function(
                parse_oracle_recovery_area(string_table)
            )
        )
        == expected_result
    )


@pytest.mark.parametrize(
    "string_table, item, expected_result",
    [
        (
            _AGENT_OUTPUT,
            "AIMDWHD1",
            [
                Result(
                    state=State.CRIT,
                    summary="47.9 GiB out of 50.0 GiB used (95.1%, warn/crit at 70.0%/90.0%), 300 MiB reclaimable",
                ),
                Metric("used", 49000.0, levels=(35864.5, 46111.5), boundaries=(0.0, 51235.0)),
                Metric("reclaimable", 300.0),
            ],
        ),
    ],
)
def test_check_oracle_recovery_area(
    string_table: StringTable,
    item: str,
    expected_result: CheckResult,
) -> None:
    assert (
        list(
            check_plugin_oracle_recovery_area.check_function(
                item=item,
                params={
                    "levels": (70.0, 90.0),
                },
                section=parse_oracle_recovery_area(string_table),
            )
        )
        == expected_result
    )


@pytest.mark.parametrize(
    "string_table, expected_result",
    [
        ([], []),
        (
            _AGENT_OUTPUT,
            [
                TableRow(
                    path=["software", "applications", "oracle", "recovery_area"],
                    key_columns={
                        "sid": "AIMDWHD1",
                    },
                    inventory_columns={
                        "flashback": "300",
                    },
                    status_columns={},
                ),
            ],
        ),
    ],
)
def test_inventory_oracle_recovery_area(
    string_table: StringTable, expected_result: InventoryResult
) -> None:
    assert (
        list(inventory_oracle_recovery_area(parse_oracle_recovery_area(string_table)))
        == expected_result
    )


_LEGACY_ERROR_ROW = ["AIMDWHD1", "ORA-01017:", "invalid username/password"]


def test_discover_oracle_recovery_area_skips_legacy_error_row() -> None:
    assert not list(
        check_plugin_oracle_recovery_area.discovery_function(
            parse_oracle_recovery_area([_LEGACY_ERROR_ROW])
        )
    )


def test_check_oracle_recovery_area_surfaces_legacy_error() -> None:
    assert list(
        check_plugin_oracle_recovery_area.check_function(
            item="AIMDWHD1",
            params={"levels": (70.0, 90.0)},
            section=parse_oracle_recovery_area([_LEGACY_ERROR_ROW]),
        )
    ) == [
        Result(
            state=State.UNKNOWN,
            summary='Found error in agent output "ORA-01017: invalid username/password"',
        )
    ]


def test_inventory_oracle_recovery_area_skips_legacy_error_row() -> None:
    assert not list(inventory_oracle_recovery_area(parse_oracle_recovery_area([_LEGACY_ERROR_ROW])))
