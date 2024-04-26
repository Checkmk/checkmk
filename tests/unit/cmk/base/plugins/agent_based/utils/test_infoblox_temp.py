#!/usr/bin/env python3
# Copyright (C) 2023 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Callable, Mapping
from pathlib import Path

import pytest

from tests.testlib.snmp import get_parsed_snmp_section

from tests.unit.conftest import FixRegister

from cmk.utils.type_defs import CheckPluginName, SectionName

from cmk.base.api.agent_based.checking_classes import Metric, Result, Service, State

WALK_NIOS_7_2_7 = """
.1.3.6.1.4.1.7779.3.1.1.2.1.7.0 7.2.7
.1.3.6.1.4.1.7779.3.1.1.2.1.10.1.2.37 5
.1.3.6.1.4.1.7779.3.1.1.2.1.10.1.2.38 1
.1.3.6.1.4.1.7779.3.1.1.2.1.10.1.2.39 1
.1.3.6.1.4.1.7779.3.1.1.2.1.10.1.2.40 5
.1.3.6.1.4.1.7779.3.1.1.2.1.10.1.2.41 1
.1.3.6.1.4.1.7779.3.1.1.2.1.10.1.3.37 No power information available.
.1.3.6.1.4.1.7779.3.1.1.2.1.10.1.3.38 The NTP service resumed synchronization.
.1.3.6.1.4.1.7779.3.1.1.2.1.10.1.3.39 CPU_TEMP: +36.00 C
.1.3.6.1.4.1.7779.3.1.1.2.1.10.1.3.40 No temperature information available.
.1.3.6.1.4.1.7779.3.1.1.2.1.10.1.3.41 SYS_TEMP: +34.00 C
"""


WALK_NIOS_9_0_3 = """
.1.3.6.1.4.1.7779.3.1.1.2.1.7.0 9.0.3-50212
.1.3.6.1.4.1.7779.3.1.1.2.1.10.1.2.37 1
.1.3.6.1.4.1.7779.3.1.1.2.1.10.1.2.38 5
.1.3.6.1.4.1.7779.3.1.1.2.1.10.1.2.39 1
.1.3.6.1.4.1.7779.3.1.1.2.1.10.1.2.40 5
.1.3.6.1.4.1.7779.3.1.1.2.1.10.1.2.41 1
.1.3.6.1.4.1.7779.3.1.1.2.1.10.1.3.37 CPU_TEMP: +36.00 C
.1.3.6.1.4.1.7779.3.1.1.2.1.10.1.3.38 No temperature information available.
.1.3.6.1.4.1.7779.3.1.1.2.1.10.1.3.39 SYS_TEMP: +34.00 C
.1.3.6.1.4.1.7779.3.1.1.2.1.10.1.3.40
.1.3.6.1.4.1.7779.3.1.1.2.1.10.1.3.41 CPU Usage: 20%
"""


@pytest.mark.usefixtures("fix_register")
@pytest.mark.parametrize(
    ["input_walk"],
    [
        pytest.param(WALK_NIOS_7_2_7, id="Nios 7.2.7"),
        pytest.param(WALK_NIOS_9_0_3, id="Nios 9.0.3"),
    ],
)
def test_parse_infoblox_temp(input_walk: str, as_path: Callable[[str], Path]) -> None:
    section = get_parsed_snmp_section(SectionName("infoblox_temp"), as_path(input_walk))
    assert section == {
        "CPU_TEMP 1": {"reading": 36.0, "state": (0, "working"), "unit": "C"},
        "No temperature information available. 2": {
            "reading": None,
            "state": (3, "unknown"),
            "unit": None,
        },
        "SYS_TEMP": {"reading": 34.0, "state": (0, "working"), "unit": "C"},
    }


@pytest.mark.usefixtures("fix_register")
@pytest.mark.parametrize(
    ["input_walk"],
    [
        pytest.param(WALK_NIOS_7_2_7, id="Nios 7.2.7"),
        pytest.param(WALK_NIOS_9_0_3, id="Nios 9.0.3"),
    ],
)
def test_inventory_infoblox_temp(
    fix_register: FixRegister, input_walk: str, as_path: Callable[[str], Path]
) -> None:
    section = get_parsed_snmp_section(SectionName("infoblox_temp"), as_path(input_walk))
    assert section is not None
    assert list(
        fix_register.check_plugins[CheckPluginName("infoblox_temp")].discovery_function(section)
    ) == [Service(item="CPU_TEMP 1"), Service(item="SYS_TEMP")]


@pytest.mark.usefixtures("fix_register")
@pytest.mark.parametrize(
    ["input_walk"],
    [
        pytest.param(WALK_NIOS_7_2_7, id="Nios 7.2.7"),
        pytest.param(WALK_NIOS_9_0_3, id="Nios 9.0.3"),
    ],
)
@pytest.mark.parametrize(
    ["item", "params", "expected"],
    [
        pytest.param(
            "CPU_TEMP 1",
            {"levels": (40.0, 50.0)},
            [Result(state=State.OK, summary="36.0 °C"), Metric("temp", 36.0, levels=(40.0, 50.0))],
            id="ok",
        ),
        pytest.param(
            "SYS_TEMP",
            {"levels": (30.0, 40.0)},
            [
                Result(state=State.WARN, summary="34.0 °C (warn/crit at 30.0/40.0 °C)"),
                Metric("temp", 34.0, levels=(30.0, 40.0)),
            ],
            id="warning",
        ),
        pytest.param(
            "SYS_TEMP",
            {"levels": (20.0, 30.0)},
            [
                Result(state=State.CRIT, summary="34.0 °C (warn/crit at 20.0/30.0 °C)"),
                Metric("temp", 34.0, levels=(20.0, 30.0)),
            ],
            id="error",
        ),
    ],
)
def test_check_infoblox_temp(
    fix_register: FixRegister,
    input_walk: str,
    item: str,
    params: Mapping[str, tuple[float, float]],
    expected: list,
    as_path: Callable[[str], Path],
) -> None:
    section = get_parsed_snmp_section(SectionName("infoblox_temp"), as_path(input_walk))
    assert section is not None

    assert (
        list(
            fix_register.check_plugins[CheckPluginName("infoblox_temp")].check_function(
                item=item, params=params, section=section
            )
        )
        == expected
    )
