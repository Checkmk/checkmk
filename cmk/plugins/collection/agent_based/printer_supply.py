#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import enum
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from typing import Any, Final

from cmk.agent_based.v1 import check_levels as check_levels_v1
from cmk.agent_based.v2 import (
    all_of,
    CheckPlugin,
    CheckResult,
    DiscoveryResult,
    Metric,
    not_matches,
    OIDEnd,
    render,
    Result,
    Service,
    SNMPSection,
    SNMPTree,
    State,
    StringTable,
)
from cmk.plugins.lib.constants import OID_SYS_OBJ
from cmk.plugins.lib.printer import DETECT_PRINTER

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


class SupplyClass(enum.Enum):
    CONTAINER = enum.auto()
    RECEPTACLE = enum.auto()


@dataclass(frozen=True)
class PrinterSupply:
    unit: str
    max_capacity: int
    level: int
    supply_class: SupplyClass
    color: str

    @property
    def capacity_unrestricted(self) -> bool:
        return self.max_capacity == -1

    @property
    def capacity_unknown(self) -> bool:
        return self.max_capacity == -2

    @property
    def level_unrestricted(self) -> bool:
        return self.level == -1

    @property
    def level_unknown(self) -> bool:
        return self.level == -2

    @property
    def some_level_remains(self) -> bool:
        return self.level == -3

    @property
    def has_partial_data(self) -> bool:
        return (
            self.capacity_unknown
            or self.level_unrestricted
            or self.level_unknown
            or self.some_level_remains
        )


Section = dict[str, PrinterSupply]


def _get_oid_end_last_index(oid_end: str) -> str:
    # return last number of OID_END
    return oid_end.split(".")[-1]


def get_unit(unit_info: str) -> str:
    unit = MAP_UNIT.get(unit_info, "")
    return unit if unit in ("", "%") else f" {unit}"


def parse_printer_supply(string_table: Sequence[StringTable]) -> Section:
    if len(string_table) < 2:
        return {}

    parsed = {}
    colors = []

    color_mapping = {_get_oid_end_last_index(oid_end): value for oid_end, value in string_table[0]}

    for index, (
        name,
        unit_info,
        raw_max_capacity,
        raw_level,
        raw_supply_class,
        color_id,
    ) in enumerate(string_table[1]):
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
                name = f"{color.title()} {name}"

        # fix trailing zero bytes (seen on HP Jetdirect 143 and 153)
        description = name.split(" S/N:")[0].strip("\0")
        color = color.rstrip("\0")
        unit = get_unit(unit_info)

        parsed[description] = PrinterSupply(
            unit,
            max_capacity,
            level,
            # When unit type is
            # 1 = other
            # 3 = supplyThatIsConsumed
            # 4 = supplyThatIsFilled
            # the value is contains the current level if this supply is a container
            # but when the remaining space if this supply is a receptacle
            #
            # This table can be missing on some devices. Assume type 3 in this case.
            SupplyClass.RECEPTACLE if raw_supply_class == "4" else SupplyClass.CONTAINER,
            color,
        )

    return parsed


snmp_section_printer_supply = SNMPSection(
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

    if supply.has_partial_data:  # no percentage possible
        if supply.level_unrestricted or supply.capacity_unrestricted:
            yield Result(
                state=State.OK, summary="%sThere are no restrictions on this supply" % color_info
            )
            return

        if supply.some_level_remains:
            yield _check_some_remaining(supply, params, color_info)
            return

        if supply.level_unknown:
            yield Result(state=State.UNKNOWN, summary="%s Unknown level" % color_info)
            return

        if supply.capacity_unknown:
            # no percentage possible. We compare directly against levels
            yield Result(state=State.OK, summary="%sLevel: %d" % (color_info, supply.level))
            yield Metric("pages", supply.level)
            return

    leftperc = 100.0 * supply.level / supply.max_capacity
    if supply.supply_class is SupplyClass.RECEPTACLE:
        leftperc = 100 - leftperc

    # Some printers handle the used / remaining material differently
    # With the upturn option we can toggle the point of view (again)
    if params["upturn_toner"]:
        leftperc = 100 - leftperc

    yield from check_levels_v1(
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


def _check_some_remaining(
    supply: PrinterSupply, params: Mapping[str, Any], color_info: str
) -> Result:
    match supply.supply_class:
        case SupplyClass.CONTAINER:
            return Result(
                state=State(params["some_remaining_ink"]),
                summary=f"{color_info}Some ink remaining",
            )
        case SupplyClass.RECEPTACLE:
            return Result(
                state=State(params["some_remaining_space"]),
                summary=f"{color_info}Some space remaining",
            )


DEFAULT_PARAMETERS = {
    "levels": (20.0, 10.0),
    "upturn_toner": False,
    "some_remaining_ink": 1,
    "some_remaining_space": 1,
}


check_plugin_printer_supply = CheckPlugin(
    name="printer_supply",
    service_name="Supply %s",
    discovery_function=discovery_printer_supply,
    check_function=check_printer_supply,
    check_ruleset_name="printer_supply",
    check_default_parameters=DEFAULT_PARAMETERS,
)
