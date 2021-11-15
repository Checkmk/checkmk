#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from typing import Any, Dict, Final, List, Mapping, NamedTuple

from .agent_based_api.v1 import (
    all_of,
    check_levels,
    Metric,
    not_matches,
    OIDEnd,
    register,
    render,
    Result,
    Service,
    SNMPTree,
    State,
)
from .agent_based_api.v1.type_defs import CheckResult, DiscoveryResult, StringTable
from .utils.constants import OID_SYS_OBJ
from .utils.printer import DETECT_PRINTER

MAP_UNIT: Final = {
    "3": "ten thousandths of inches",
    "4": "micrometers",
    "7": "impressions",
    "8": "sheets",
    "11": "hours",
    "12": "thousandths of ounces",
    "13": "tenths of grams",
    "14": "hundreths of fluid ounces",
    "15": "tenths of milliliters",
    "16": "feet",
    "17": "meters",
    "18": "items",
    "19": "%",
}


class PrinterSupply(NamedTuple):
    unit: str
    max_capacity: int
    level: int
    supply_class: str
    color: str


Section = Dict[str, PrinterSupply]


def _get_oid_end_last_index(oid_end: str) -> str:
    # return last number of OID_END
    return oid_end.split(".")[-1]


def get_unit(unit_info: str) -> str:
    unit = MAP_UNIT.get(unit_info, "")
    return unit if unit in ("", "%") else f" {unit}"


def parse_printer_supply(string_table: List[StringTable]) -> Section:
    if len(string_table) < 2:
        return {}

    parsed = {}
    colors = []

    color_mapping = {_get_oid_end_last_index(oid_end): value for oid_end, value in string_table[0]}

    for index, (name, unit_info, raw_max_capacity, raw_level, supply_class, color_id) in enumerate(
        string_table[1]
    ):

        try:
            max_capacity = int(raw_max_capacity)
            level = int(raw_level)
        except ValueError:
            continue
        # Ignore devices which show -2 for current value and -2 for max value -> useless
        if max_capacity == -2 and level == -2:
            continue

        # Assume 100% as maximum when 0 is reported
        # Saw some toner cartridge reporting value=0 and max_capacity=0 on empty toner
        if max_capacity == 0:
            max_capacity = 100

        color = color_mapping.get(color_id, "")
        # For toners or drum units add the color (if available)
        if name.startswith("Toner Cartridge") or name.startswith("Image Drum Unit"):
            if color:
                colors += [color]
            elif color == "" and colors:
                color = colors[index - len(colors)]
            if color:
                name = "%s %s" % (color.title(), name)

        # fix trailing zero bytes (seen on HP Jetdirect 143 and 153)
        description = name.split(" S/N:")[0].strip("\0")
        color = color.rstrip("\0")
        unit = get_unit(unit_info)

        parsed[description] = PrinterSupply(unit, max_capacity, level, supply_class, color)

    return parsed


register.snmp_section(
    name="printer_supply",
    detect=all_of(DETECT_PRINTER, not_matches(OID_SYS_OBJ, ".1.3.6.1.4.1.367.1.1")),
    parse_function=parse_printer_supply,
    fetch=[
        SNMPTree(
            base=".1.3.6.1.2.1.43.12.1.1",
            oids=[
                OIDEnd(),
                "4",  # Printer-MIB::prtMarkerColorantValue
            ],
        ),
        SNMPTree(
            base=".1.3.6.1.2.1.43.11.1.1",
            oids=[
                "6",  # Printer-MIB::prtMarkerSuppliesDescription
                "7",  # Printer-MIB::prtMarkerSuppliesUnit
                "8",  # Printer-MIB::prtMarkerSuppliesMaxCapacity
                "9",  # Printer-MIB::prtMarkerSuppliesLevel
                "4",  # Printer-MIB::prtMarkerSuppliesClass
                "3",  # Printer-MIB:prtMarkerSuppliesColorantIndex
            ],
        ),
    ],
)


def discovery_printer_supply(section: Section) -> DiscoveryResult:
    for key in section.keys():
        yield Service(item=key)


def check_printer_supply(item: str, params: Mapping[str, Any], section: Section) -> CheckResult:
    supply = section.get(item)
    if supply is None:
        return

    color_info = ""
    if supply.color and supply.color.lower() not in item.lower():
        color_info = "[%s] " % supply.color

    warn, crit = params["levels"]

    # handle cases with partial data
    if supply.max_capacity == -2 or supply.level in [-3, -2, -1]:  # no percentage possible
        if supply.level == -1 or supply.max_capacity == -1:
            yield Result(
                state=State.OK, summary="%sThere are no restrictions on this supply" % color_info
            )
            return
        if supply.level == -3:
            yield Result(
                state=State(params["some_remaining"]), summary="%sSome remaining" % color_info
            )
            yield Metric(
                "pages",
                supply.level,
                levels=(0.01 * warn * supply.max_capacity, 0.01 * crit * supply.max_capacity),
                boundaries=(0, supply.max_capacity),
            )
            return
        if supply.level == -2:
            yield Result(state=State.UNKNOWN, summary="%s Unknown level" % color_info)
            return
        if supply.max_capacity == -2:
            # no percentage possible. We compare directly against levels
            yield Result(state=State.OK, summary="%sLevel: %d" % (color_info, supply.level))
            yield Metric("pages", supply.level)
            return

    leftperc = 100.0 * supply.level / supply.max_capacity
    # When unit type is
    # 1 = other
    # 3 = supplyThatIsConsumed
    # 4 = supplyThatIsFilled
    # the value is contains the current level if this supply is a container
    # but when the remaining space if this supply is a receptacle
    #
    # This table can be missing on some devices. Assume type 3 in this case.
    if supply.supply_class == "4":
        leftperc = 100 - leftperc

    # Some printers handle the used / remaining material differently
    # With the upturn option we can toggle the point of view (again)
    if params["upturn_toner"]:
        leftperc = 100 - leftperc

    yield from check_levels(
        leftperc,
        levels_lower=(warn, crit),
        label=f"{color_info}Remaining",
        render_func=render.percent,
    )

    summary = f"Supply: {supply.level} of max. {supply.max_capacity}{supply.unit}"
    yield Result(state=State.OK, summary=summary)
    yield Metric(
        "pages",
        supply.level,
        levels=(0.01 * warn * supply.max_capacity, 0.01 * crit * supply.max_capacity),
        boundaries=(0, supply.max_capacity),
    )


register.check_plugin(
    name="printer_supply",
    service_name="Supply %s",
    discovery_function=discovery_printer_supply,
    check_function=check_printer_supply,
    check_ruleset_name="printer_supply",
    check_default_parameters={"levels": (20.0, 10.0), "upturn_toner": False, "some_remaining": 1},
)
