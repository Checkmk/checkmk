#!/usr/bin/env python3
# Copyright (C) 2023 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
from collections.abc import Callable, Mapping
from pathlib import Path

import pytest

from tests.testlib.snmp import get_parsed_snmp_section

from cmk.utils.sectionname import SectionName

from cmk.base.legacy_checks.infoblox_temp import check_infoblox_temp, inventory_infoblox_temp

WALK = """
.1.3.6.1.4.1.7779.3.1.1.2.1.10.1.2.39 1
.1.3.6.1.4.1.7779.3.1.1.2.1.10.1.2.40 5
.1.3.6.1.4.1.7779.3.1.1.2.1.10.1.2.41 1
.1.3.6.1.4.1.7779.3.1.1.2.1.10.1.3.39 CPU_TEMP: +36.00 C
.1.3.6.1.4.1.7779.3.1.1.2.1.10.1.3.40 No temperature information available.
.1.3.6.1.4.1.7779.3.1.1.2.1.10.1.3.41 SYS_TEMP: +34.00 C
"""


@pytest.mark.usefixtures("fix_register")
def test_parse_infoblox_temp(as_path: Callable[[str], Path]) -> None:
    section = get_parsed_snmp_section(SectionName("infoblox_temp"), as_path(WALK))
    assert section == {
        "CPU_TEMP 1": {"reading": 36.0, "state": (0, "working"), "unit": "c"},
        "SYS_TEMP": {"reading": 34.0, "state": (0, "working"), "unit": "c"},
    }


@pytest.mark.usefixtures("fix_register")
def test_inventory_infoblox_temp(as_path: Callable[[str], Path]) -> None:
    section = get_parsed_snmp_section(SectionName("infoblox_temp"), as_path(WALK))
    assert section is not None
    assert list(inventory_infoblox_temp(section)) == [("CPU_TEMP 1", {}), ("SYS_TEMP", {})]


@pytest.mark.usefixtures("fix_register")
@pytest.mark.parametrize(
    ["item", "params", "expected"],
    [
        pytest.param(
            "CPU_TEMP 1",
            {"levels": (40.0, 50.0)},
            [0, "36.0 °C", [("temp", 36.0, 40.0, 50.0)]],
            id="ok",
        ),
        pytest.param(
            "SYS_TEMP",
            {"levels": (30.0, 40.0)},
            [1, "34.0 °C (warn/crit at 30.0/40.0 °C)", [("temp", 34.0, 30.0, 40.0)]],
            id="warning",
        ),
        pytest.param(
            "SYS_TEMP",
            {"levels": (20.0, 30.0)},
            [2, "34.0 °C (warn/crit at 20.0/30.0 °C)", [("temp", 34.0, 20.0, 30.0)]],
            id="error",
        ),
    ],
)
def test_check_infoblox_temp(
    as_path: Callable[[str], Path],
    item: str,
    params: Mapping[str, tuple[float, float]],
    expected: list,
) -> None:
    section = get_parsed_snmp_section(SectionName("infoblox_temp"), as_path(WALK))
    assert section is not None

    assert list(check_infoblox_temp(item, params, section)) == expected
