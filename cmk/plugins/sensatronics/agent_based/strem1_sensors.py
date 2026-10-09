#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# Author: Lars Michelsen <lm@mathias-kettner.de>, 2011-03-21


from collections.abc import Sequence

from cmk.agent_based.v2 import (
    CheckPlugin,
    CheckResult,
    contains,
    DiscoveryResult,
    Metric,
    Result,
    Service,
    SNMPSection,
    SNMPTree,
    State,
    StringTable,
)

Section = Sequence[StringTable]


def strem1_sensors_parse_info(info: StringTable) -> list[list[str]]:
    # Change format of output: 1 tuple for each group
    parsed = []
    for group in zip(*info):
        grp = group[0]

        items = group[1:]
        for i in range(0, len(items), 3):
            parsed.append([grp + " " + items[i]] + list(items[i : i + 3]))
    return parsed


def discover_strem1_sensors(section: Section) -> DiscoveryResult:
    yield from (
        Service(item=index)
        for index, _typ, val, _intval in strem1_sensors_parse_info(section[1])
        if val != "-999.9"
    )


def check_strem1_sensors(item: str, section: Section) -> CheckResult:
    for index, typ, val, _intval in strem1_sensors_parse_info(section[1]):
        if index == item:
            uom = section[0][0][0] if typ == "Temperature" else "%"
            val_f = float(val)
            warn: float | None
            crit: float | None
            (warn, crit) = (None, None) if typ in {"Humidity", "Wetness"} else (28.0, 32.0)

            infotext = f"{val_f:.1f}{uom}"
            thrtext = []
            if warn is not None:
                thrtext.append(f"warn at {warn:.1f}{uom}")
            if crit is not None:
                thrtext.append(f"crit at {crit:.1f}{uom}")
            if thrtext:
                infotext += f" ({', '.join(thrtext)})"

            if crit is not None and val_f >= crit:
                state = State.CRIT
            elif warn is not None and val_f >= warn:
                state = State.WARN
            else:
                state = State.OK

            yield Result(state=state, summary=f"{typ} is: {infotext}")
            yield Metric(typ.lower(), val_f, levels=(warn, crit))
            return
    yield Result(state=State.UNKNOWN, summary="Sensor not found")


def parse_strem1_sensors(string_table: Sequence[StringTable]) -> Section:
    return string_table


snmp_section_strem1_sensors = SNMPSection(
    name="strem1_sensors",
    parse_function=parse_strem1_sensors,
    detect=contains(".1.3.6.1.2.1.1.1.0", "Sensatronics EM1"),
    fetch=[
        SNMPTree(
            base=".1.3.6.1.4.1.16174.1.1.3.2.3",
            oids=["1"],
        ),
        SNMPTree(
            base=".1.3.6.1.4.1.16174.1.1.3.3",
            oids=["1", "2", "3", "4"],
        ),
    ],
)

check_plugin_strem1_sensors = CheckPlugin(
    name="strem1_sensors",
    service_name="Sensor - %s",
    discovery_function=discover_strem1_sensors,
    check_function=check_strem1_sensors,
)
