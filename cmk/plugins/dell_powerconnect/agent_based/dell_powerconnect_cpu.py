#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Mapping
from dataclasses import dataclass

from cmk.agent_based.v1 import (
    check_levels,
)
from cmk.agent_based.v2 import (
    CheckPlugin,
    CheckResult,
    contains,
    DiscoveryResult,
    Metric,
    render,
    Service,
    SimpleSNMPSection,
    SNMPTree,
    StringTable,
)


@dataclass(frozen=True)
class Section:
    enabled: bool
    onesecondperc: float
    oneminuteperc: float
    fiveminutesperc: float


def parse_dell_powerconnect_cpu(string_table: StringTable) -> Section | None:
    if not string_table or not string_table[0]:
        return None

    enabled_raw, onesecondperc, oneminuteperc, fiveminutesperc = string_table[0]
    enabled = enabled_raw == "1"
    if onesecondperc == "":
        return None

    if not enabled:
        return None

    return Section(
        enabled=enabled,
        onesecondperc=int(onesecondperc),
        oneminuteperc=int(oneminuteperc),
        fiveminutesperc=int(fiveminutesperc),
    )


snmp_section_dell_powerconnect_cpu = SimpleSNMPSection(
    name="dell_powerconnect_cpu",
    detect=contains(".1.3.6.1.2.1.1.2.0", ".1.3.6.1.4.1.674.10895"),
    fetch=SNMPTree(
        base=".1.3.6.1.4.1.89.1",
        oids=["6", "7", "8", "9"],
    ),
    parse_function=parse_dell_powerconnect_cpu,
)


def discover_dell_powerconnect_cpu(section: Section) -> DiscoveryResult:
    if section.enabled and section.onesecondperc >= 0:
        yield Service()


def check_dell_powerconnect_cpu(
    params: Mapping[str, tuple[float, float]], section: Section
) -> CheckResult:
    if not section.enabled or section.onesecondperc < 0 or section.onesecondperc > 100:
        return

    # Darn. It again happend. Someone mixed up load and utilization.
    # We do *not* rename the performance variables here, in order not
    # to mix up existing RRDs...
    yield from check_levels(
        section.onesecondperc,
        metric_name="util",
        label="CPU utilization",
        levels_upper=params["levels"],
        render_func=render.percent,
        boundaries=(0, 100),
    )
    yield Metric("util1", section.oneminuteperc, boundaries=(0, 100))
    yield Metric("util5", section.fiveminutesperc, boundaries=(0, 100))


check_plugin_dell_powerconnect_cpu = CheckPlugin(
    name="dell_powerconnect_cpu",
    service_name="CPU utilization",
    discovery_function=discover_dell_powerconnect_cpu,
    check_function=check_dell_powerconnect_cpu,
    check_default_parameters={"levels": (80.0, 90.0)},
)
