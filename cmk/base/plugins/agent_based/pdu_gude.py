#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from dataclasses import dataclass
from typing import Iterable, Mapping, Tuple

from .agent_based_api.v1 import check_levels, equals, register, Service, SNMPTree
from .agent_based_api.v1.type_defs import CheckResult, DiscoveryResult, StringTable


@dataclass(frozen=True)
class GudePDUProperty:
    value: float
    unit: str
    label: str


Section = Mapping[str, Iterable[GudePDUProperty]]

_UNIT_SCALE_LABEL = (
    (
        "kWh",
        1000,
        "Total accumulated active energy",
    ),
    (
        "W",
        1,
        "Active power",
    ),
    (
        "A",
        1000,
        "Current",
    ),
    (
        "V",
        1,
        "Voltage",
    ),
    (
        "VA",
        1,
        "Mean apparent power",
    ),
)


def parse_pdu_gude(string_table: StringTable) -> Section:
    return {
        str(idx): [
            GudePDUProperty(
                float(value_str) / scale,
                unit,
                label,
            )
            for value_str, (unit, scale, label) in zip(
                pdu_data,
                _UNIT_SCALE_LABEL,
            )
        ]
        for idx, pdu_data in enumerate(
            string_table,
            start=1,
        )
    }


register.snmp_section(
    name="pdu_gude_8301",
    parsed_section_name="pdu_gude",
    parse_function=parse_pdu_gude,
    detect=equals(
        ".1.3.6.1.2.1.1.2.0",
        ".1.3.6.1.4.1.28507.26",
    ),
    fetch=SNMPTree(
        ".1.3.6.1.4.1.28507.26.1.5.1.2.1",
        [
            "3",  # Consumption
            "4",  # Power
            "5",  # Current
            "6",  # Voltage
            "10",  # Track power
        ],
    ),
)


register.snmp_section(
    name="pdu_gude_8310",
    parsed_section_name="pdu_gude",
    parse_function=parse_pdu_gude,
    detect=equals(
        ".1.3.6.1.2.1.1.2.0",
        ".1.3.6.1.4.1.28507.27",
    ),
    fetch=SNMPTree(
        ".1.3.6.1.4.1.28507.27.1.5.1.2.1",
        [
            "3",  # Consumption
            "4",  # Power
            "5",  # Current
            "6",  # Voltage
            "10",  # Track power
        ],
    ),
)


register.snmp_section(
    name="pdu_gude_8801",
    parsed_section_name="pdu_gude",
    parse_function=parse_pdu_gude,
    detect=equals(
        ".1.3.6.1.2.1.1.2.0",
        ".1.3.6.1.4.1.28507.41",
    ),
    fetch=SNMPTree(
        ".1.3.6.1.4.1.28507.41.1.5.1.2.1",
        [
            "3",  # Consumption
            "4",  # Power
            "5",  # Current
            "6",  # Voltage
            "10",  # Track power
        ],
    ),
)


def discover_pdu_gude(section: Section) -> DiscoveryResult:
    yield from (Service(item=pdu_num) for pdu_num in section)


def check_pdu_gude(
    item: str,
    params: Mapping[str, Tuple[float, float]],
    section: Section,
) -> CheckResult:
    if not (pdu_properties := section.get(item)):
        return

    for pdu_property in pdu_properties:
        levels_lower = levels_upper = None

        if pdu_property.unit in params:
            warn, crit = params[pdu_property.unit]
            if warn > crit:
                levels_lower = warn, crit
            else:
                levels_upper = warn, crit

        yield from check_levels(
            pdu_property.value,
            levels_upper=levels_upper,
            levels_lower=levels_lower,
            metric_name=pdu_property.unit,
            render_func=lambda v: f"{v:.2f} {pdu_property.unit}",  # pylint: disable=cell-var-from-loop
            label=pdu_property.label,
        )


register.check_plugin(
    name="pdu_gude",
    service_name="Phase %s",
    discovery_function=discover_pdu_gude,
    check_function=check_pdu_gude,
    check_ruleset_name="pdu_gude",
    check_default_parameters={
        "V": (220, 210),
        "A": (15, 16),
        "W": (3500, 3600),
    },
)
