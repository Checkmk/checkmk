#!/usr/bin/env python3
# Copyright (C) 2022 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# mypy: disable-error-code="misc"
# mypy: disable-error-code="type-arg"


from typing import Any, cast

import pytest

from cmk.agent_based.v2 import (
    CheckResult,
    DiscoveryResult,
    Metric,
    Result,
    Service,
    SimpleSNMPSection,
    State,
    StringTable,
)
from cmk.plugins.apc.agent_based.apc_symmetra_power import snmp_section_apc_symmetra_power
from cmk.plugins.collection.agent_based.epower import check_epower, discover_epower
from cmk.plugins.ups.agent_based.ups_power import snmp_section_ups_power

# SUP-12323
TABLE_APC_0: StringTable = [["1", "1309"], ["2", "1344"], ["3", "1783"]]

TABLE_APC_1: StringTable = [
    ["1", "4000"],
    ["2", "2000"],
    ["3", "3000"],
    ["12", "-1"],
    ["23", "-1"],
    ["31", "-1"],
]

TABLE_UPS_0: StringTable = [["1", "2300"], ["2", "3500"], ["3", "4800"]]

TABLE_UPS_1: StringTable = [["1", "0"], ["2", "3500"], ["3", "4800"]]


@pytest.mark.parametrize(
    "table, section, result",
    [
        pytest.param(
            TABLE_APC_0,
            snmp_section_apc_symmetra_power,
            [
                Service(item="1"),
                Service(item="2"),
                Service(item="3"),
            ],
            id="apc-symmetra-0",
        ),
        pytest.param(
            TABLE_APC_1,
            snmp_section_apc_symmetra_power,
            [
                Service(item="1"),
                Service(item="2"),
                Service(item="3"),
            ],
            id="apc-symmetra-1",
        ),
        pytest.param(
            TABLE_UPS_0,
            snmp_section_ups_power,
            [
                Service(item="1"),
                Service(item="2"),
                Service(item="3"),
            ],
            id="ups-power-0",
        ),
    ],
)
def test_power_discover(
    table: StringTable,
    section: SimpleSNMPSection,
    result: DiscoveryResult,
) -> None:
    parsed = cast(dict[str, int], section.parse_function([table]))

    assert list(discover_epower(parsed)) == result


@pytest.mark.parametrize(
    "table, section, item, params, result",
    [
        pytest.param(
            TABLE_APC_0,
            snmp_section_apc_symmetra_power,
            "1",
            {
                "levels_lower": (20, 1),
                "levels_upper": None,
            },
            [
                Result(state=State.OK, summary="Power: 1309 W"),
                Metric("power", 1309.0),
            ],
            id="apc-symmetra-0",
        ),
        pytest.param(
            TABLE_APC_1,
            snmp_section_apc_symmetra_power,
            "2",
            {"levels_lower": (20, 1), "levels_upper": None},
            [
                Result(state=State.OK, summary="Power: 2000 W"),
                Metric("power", 2000.0),
            ],
            id="apc-symmetra-1",
        ),
        pytest.param(
            TABLE_APC_1,
            snmp_section_apc_symmetra_power,
            "2",
            {"levels_lower": (3000, 2000), "levels_upper": None},
            [
                Result(state=State.WARN, summary="Power: 2000 W (warn/crit below 3000 W/2000 W)"),
                Metric("power", 2000.0),
            ],
            id="apc-symmetra-1-warn",
        ),
        pytest.param(
            TABLE_APC_1,
            snmp_section_apc_symmetra_power,
            "2",
            {"levels_lower": (6000, 3000), "levels_upper": None},
            [
                Result(state=State.CRIT, summary="Power: 2000 W (warn/crit below 6000 W/3000 W)"),
                Metric("power", 2000.0),
            ],
            id="apc-symmetra-1-crit",
        ),
        pytest.param(
            TABLE_UPS_0,
            snmp_section_ups_power,
            "2",
            {"levels_lower": (20, 1), "levels_upper": None},
            [
                Result(state=State.OK, summary="Power: 3500 W"),
                Metric("power", 3500.0),
            ],
            id="ups-power-2-ok",
        ),
        pytest.param(
            TABLE_UPS_0,
            snmp_section_ups_power,
            "2",
            {"levels_lower": (4000, 3000), "levels_upper": None},
            [
                Result(state=State.WARN, summary="Power: 3500 W (warn/crit below 4000 W/3000 W)"),
                Metric("power", 3500.0),
            ],
            id="ups-power-2-warn",
        ),
        pytest.param(
            TABLE_UPS_0,
            snmp_section_ups_power,
            "2",
            {"levels_lower": (6000, 4000), "levels_upper": None},
            [
                Result(state=State.CRIT, summary="Power: 3500 W (warn/crit below 6000 W/4000 W)"),
                Metric("power", 3500.0),
            ],
            id="ups-power-2-crit",
        ),
        pytest.param(
            TABLE_UPS_1,
            snmp_section_ups_power,
            "1",
            {"levels_lower": (4000, 3000), "levels_upper": None},
            [
                Result(state=State.CRIT, summary="Power: 0 W (warn/crit below 4000 W/3000 W)"),
                Metric("power", 0.0),
            ],
            id="ups-power is 0",
        ),
        pytest.param(
            TABLE_UPS_0,
            snmp_section_ups_power,
            "2",
            {"levels_lower": (3000, 2000), "levels_upper": (3000, 4000)},
            [
                Result(state=State.WARN, summary="Power: 3500 W (warn/crit at 3000 W/4000 W)"),
                Metric("power", 3500.0, levels=(3000.0, 4000.0)),
            ],
            id="ups-power-2-crit",
        ),
    ],
)
def test_epower_check(
    table: StringTable,
    section: SimpleSNMPSection,
    item: str,
    params: Any,
    result: CheckResult,
) -> None:
    parsed = cast(dict[str, int], section.parse_function([table]))

    assert list(check_epower(item=item, params=params, section=parsed)) == result
