#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# F5OS rSeries platform fans
# MIB: F5-PLATFORM-STATS-MIB (enterprise .1.3.6.1.4.1.12276.1)

from typing import TypedDict

from cmk.agent_based.v2 import (
    CheckPlugin,
    CheckResult,
    DiscoveryResult,
    Service,
    SimpleSNMPSection,
    SNMPTree,
    StringTable,
)
from cmk.plugins.f5os_rseries.lib.detect import DETECT_F5OS_RSERIES
from cmk.plugins.lib.fan import check_fan


def parse_f5os_rseries_fan(string_table: StringTable) -> dict[str, float]:
    """Expand 8 fan-speed columns from one row into 8 keyed items.

    Columns that the model does not populate come back as empty strings and are
    skipped, so smaller models do not get phantom fan services. A populated column
    reading ``0`` is kept: that represents a stalled fan and must still be
    discovered so the lower speed threshold can raise an alert on it.
    """
    if not string_table:
        return {}
    row = string_table[0]
    result: dict[str, float] = {}
    for i, raw in enumerate(row[:8], start=1):
        # An empty column is a fan slot this model does not populate (the MIB defines
        # more fan columns than any single model uses) and is skipped so we do not invent
        # a phantom fan. A populated column is converted directly: a genuine ``0`` is a
        # stalled fan and is kept so the lower threshold can alert on it, while a
        # non-numeric value is unexpected and is allowed to surface rather than be hidden.
        if raw.strip() == "":
            continue
        result[f"Fan {i}"] = float(raw)
    return result


snmp_section_f5os_rseries_fan = SimpleSNMPSection(
    name="f5os_rseries_fan",
    parse_function=parse_f5os_rseries_fan,
    detect=DETECT_F5OS_RSERIES,
    fetch=SNMPTree(
        base=".1.3.6.1.4.1.12276.1.2.1.7.1.1",
        oids=[
            "1",  # fan-1-speed (unit: 1 RPM)
            "2",  # fan-2-speed (unit: 1 RPM)
            "3",  # fan-3-speed (unit: 1 RPM)
            "4",  # fan-4-speed (unit: 1 RPM)
            "5",  # fan-5-speed (unit: 1 RPM)
            "6",  # fan-6-speed (unit: 1 RPM)
            "7",  # fan-7-speed (unit: 1 RPM)
            "8",  # fan-8-speed (unit: 1 RPM)
        ],
    ),
)


def discover_f5os_rseries_fan(section: dict[str, float]) -> DiscoveryResult:
    for item in section:
        yield Service(item=item)


class _FanParams(TypedDict, total=False):
    lower: tuple[float, float]
    upper: tuple[float, float]
    output_metrics: bool


def check_f5os_rseries_fan(item: str, params: _FanParams, section: dict[str, float]) -> CheckResult:
    speed = section.get(item)
    if speed is None:
        return
    yield from check_fan(speed, params)


check_plugin_f5os_rseries_fan = CheckPlugin(
    name="f5os_rseries_fan",
    sections=["f5os_rseries_fan"],
    service_name="F5OS Fan Speed %s",
    discovery_function=discover_f5os_rseries_fan,
    check_function=check_f5os_rseries_fan,
    check_default_parameters={"lower": (5000, 3000), "output_metrics": True},
    check_ruleset_name="hw_fans",
)
