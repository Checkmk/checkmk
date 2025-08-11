#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Mapping
from typing import Any

import pytest

from cmk.agent_based.v2 import (
    CheckResult,
    DiscoveryResult,
    Metric,
    Result,
    Service,
    State,
    StringTable,
)
from cmk.plugins.lvm.agent_based.lvs import (
    check_lvm_lvs,
    discover_lvm_lvs,
    LvmLvsEntry,
    parse_lvm_lvs,
    Section,
)


@pytest.mark.parametrize(
    "string_table, expected",
    [
        pytest.param(
            [],
            {},
            id="empty",
        ),
        pytest.param(
            [
                [
                    "pool0",
                    "vg0",
                    "twi-aotz--",
                    "15.00g",
                    "",
                    "",
                    "8.87",
                    "13.55",
                    "",
                    "",
                    "",
                    "",
                ],
                [
                    "volume0",
                    "vg0",
                    "Vwi-aotz--",
                    "10.00g",
                    "pool0",
                    "",
                    "11.65",
                    "",
                    "",
                    "",
                    "",
                    "",
                ],
            ],
            {
                "vg0/pool0": LvmLvsEntry(data=8.87, meta=13.55),
            },
            id="basic_valid_input",
        ),
        pytest.param(
            [
                [
                    "volume0",
                    "vg0",
                    "wi-ao---",
                    "10.00g",
                    "",
                    "",
                    "",
                    "",
                    "",
                    "",
                    "",
                    "",
                ],
            ],
            {},
            id="empty_pool_field",
        ),
        pytest.param(
            [
                [
                    "pool0",
                    "vg0",
                    "twi-aotz--",
                    "15.00g",
                    "",
                    "",
                    "8.87",
                    "13.55",
                    "",
                    "",
                    "",
                    "",
                ],
            ],
            {},
            id="no_volume_referencing_pool",
        ),
        pytest.param(
            [
                [
                    "pool1",
                    "vg1",
                    "wi-ao---",
                    "10.00g",
                    "pool1",
                    "",
                    "invalid",
                    "10.0",
                    "-",
                    "-",
                    "-",
                    "-",
                ],
            ],
            {},
            id="invalid_meta",
        ),
        pytest.param(
            [
                [
                    "pool1",
                    "vg1",
                    "wi-ao---",
                    "20.00g",
                    "pool1",
                    "",
                    "75.2",
                    "invalid",
                    "-",
                    "-",
                    "-",
                    "-",
                ],
            ],
            {},
            id="invalid_data",
        ),
    ],
)
def test_parse_lvm_lvs(string_table: StringTable, expected: Section) -> None:
    assert parse_lvm_lvs(string_table) == expected


@pytest.mark.parametrize(
    "string_table, expected",
    [
        pytest.param([], [], id="empty"),
        pytest.param(
            [
                [
                    "pool0",
                    "vg0",
                    "twi-aotz--",
                    "15.00g",
                    "",
                    "",
                    "8.87",
                    "13.55",
                    "",
                    "",
                    "",
                    "",
                ],
                [
                    "volume0",
                    "vg0",
                    "Vwi-aotz--",
                    "10.00g",
                    "pool0",
                    "",
                    "11.65",
                    "",
                    "",
                    "",
                    "",
                    "",
                ],
            ],
            [Service(item="vg0/pool0")],
            id="populated_section",
        ),
    ],
)
def test_discover_lvm_lvs(string_table: StringTable, expected: DiscoveryResult) -> None:
    section = parse_lvm_lvs(string_table)
    assert list(discover_lvm_lvs(section)) == expected


@pytest.mark.parametrize(
    ["item", "params", "string_table", "expected"],
    [
        pytest.param(
            "vg0/pool0",
            {
                "levels_data": ("fixed", (80.0, 90.0)),
                "levels_meta": ("fixed", (80.0, 90.0)),
            },
            [
                [
                    "pool0",
                    "vg0",
                    "twi-aotz--",
                    "15.00g",
                    "",
                    "",
                    "8.87",
                    "13.55",
                    "",
                    "",
                    "",
                    "",
                ],
                [
                    "volume0",
                    "vg0",
                    "Vwi-aotz--",
                    "10.00g",
                    "pool0",
                    "",
                    "11.65",
                    "",
                    "",
                    "",
                    "",
                    "",
                ],
            ],
            [
                Result(state=State.OK, summary="Data usage: 8.87%"),
                Metric("data_usage", 8.87, levels=(80.0, 90.0)),
                Result(state=State.OK, summary="Meta usage: 13.55%"),
                Metric("meta_usage", 13.55, levels=(80.0, 90.0)),
            ],
            id="ok",
        ),
        pytest.param(
            "vg0/pool0",
            {
                "levels_data": ("fixed", (80.0, 90.0)),
                "levels_meta": ("fixed", (80.0, 90.0)),
            },
            [
                [
                    "pool0",
                    "vg0",
                    "twi-aotz--",
                    "15.00g",
                    "",
                    "",
                    "85.87",
                    "13.55",
                    "",
                    "",
                    "",
                    "",
                ],
                [
                    "volume0",
                    "vg0",
                    "Vwi-aotz--",
                    "10.00g",
                    "pool0",
                    "",
                    "11.65",
                    "",
                    "",
                    "",
                    "",
                    "",
                ],
            ],
            [
                Result(state=State.WARN, summary="Data usage: 85.87% (warn/crit at 80.00%/90.00%)"),
                Metric("data_usage", 85.87, levels=(80.0, 90.0)),
                Result(state=State.OK, summary="Meta usage: 13.55%"),
                Metric("meta_usage", 13.55, levels=(80.0, 90.0)),
            ],
            id="data_warn",
        ),
        pytest.param(
            "vg0/pool0",
            {
                "levels_data": ("fixed", (80.0, 90.0)),
                "levels_meta": ("fixed", (80.0, 90.0)),
            },
            [
                [
                    "pool0",
                    "vg0",
                    "twi-aotz--",
                    "15.00g",
                    "",
                    "",
                    "8.87",
                    "93.55",
                    "",
                    "",
                    "",
                    "",
                ],
                [
                    "volume0",
                    "vg0",
                    "Vwi-aotz--",
                    "10.00g",
                    "pool0",
                    "",
                    "11.65",
                    "",
                    "",
                    "",
                    "",
                    "",
                ],
            ],
            [
                Result(state=State.OK, summary="Data usage: 8.87%"),
                Metric("data_usage", 8.87, levels=(80.0, 90.0)),
                Result(state=State.CRIT, summary="Meta usage: 93.55% (warn/crit at 80.00%/90.00%)"),
                Metric("meta_usage", 93.55, levels=(80.0, 90.0)),
            ],
            id="meta_crit",
        ),
    ],
)
def test_check_lvm_lvs(
    item: str, params: Mapping[str, Any], string_table: StringTable, expected: CheckResult
) -> None:
    section = parse_lvm_lvs(string_table)
    assert list(check_lvm_lvs(item, params, section)) == expected
