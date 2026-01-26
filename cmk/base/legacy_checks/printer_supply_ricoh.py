#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# mypy: disable-error-code="no-untyped-call"

# .1.3.6.1.4.1.367.3.2.1.2.24.1.1.2.1 Black Toner
# .1.3.6.1.4.1.367.3.2.1.2.24.1.1.2.2 Cyan Toner
# .1.3.6.1.4.1.367.3.2.1.2.24.1.1.2.3 Magenta Toner
# .1.3.6.1.4.1.367.3.2.1.2.24.1.1.2.4 Yellow Toner
# .1.3.6.1.4.1.367.3.2.1.2.24.1.1.5.1 30
# .1.3.6.1.4.1.367.3.2.1.2.24.1.1.5.2 20
# .1.3.6.1.4.1.367.3.2.1.2.24.1.1.5.3 30
# .1.3.6.1.4.1.367.3.2.1.2.24.1.1.5.4 -100

# some data may look like
# .1.3.6.1.4.1.367.3.2.1.2.24.1.1.2.1 Toner
# .1.3.6.1.4.1.367.3.2.1.2.24.1.1.5.1 30


from collections.abc import Mapping
from typing import Any

from cmk.agent_based.legacy.v0_unstable import LegacyCheckDefinition
from cmk.agent_based.v2 import equals, SNMPTree, StringTable

check_info = {}

Section = dict[str, int]


def parse_printer_supply_ricoh(string_table: StringTable) -> Section:
    parsed: Section = {}
    for what, pages_text in string_table:
        name_reversed = what.split(" ")

        if len(name_reversed) == 2:
            name_reversed.reverse()

        name = " ".join(name_reversed)
        parsed[name] = int(pages_text)
    return parsed


def discover_printer_supply_ricoh(parsed: Section) -> list[tuple[str, dict[str, object]]]:
    return [(key, {}) for key in parsed]


def check_printer_supply_ricoh(
    item: str, params: Mapping[str, Any] | tuple[float, ...], parsed: Section
) -> tuple[int, str, list[Any]] | None:
    def handle_regular(supply_level: int) -> tuple[int, str, int]:
        infotext = "%.0f%%" % supply_level

        if supply_level <= crit:
            state = 2
        elif supply_level <= warn:
            state = 1
        else:
            state = 0

        if state > 0:
            infotext += f" (warn/crit at {warn:.0f}%/{crit:.0f}%)"
        return state, infotext, supply_level

    def handle_negative(code: int) -> tuple[int, str, int]:
        # the following codes are based on the MP C2800
        if code == -100:
            # does not apply level. Since we don't get a proper reading
            # the best we could do would be test against 0
            return 2, "almost empty (<10%)", 0
        if code == -2:
            # cartridge removed?
            return 3, "unknown level", 0
        if code == -3:
            # -3 = full is based on user claim, but other walks also show
            # the device itself does not alert in this state
            return 0, "100%", 100
        # unknown code
        return handle_regular(0)

    if isinstance(params, tuple):
        if len(params) == 2:
            params = {"levels": params}
        else:
            params = {"levels": params[:2], "upturn_toner": params[2]}

    warn, crit = params["levels"]
    for name, supply_level in parsed.items():
        if item == name:
            if supply_level < 0:
                # negative levels usually have special meaning
                state, infotext, supply_level = handle_negative(supply_level)
            else:
                state, infotext, supply_level = handle_regular(supply_level)

            if "black" in name.lower():
                perf_type = "black"
            elif "cyan" in name.lower():
                perf_type = "cyan"
            elif "magenta" in name.lower():
                perf_type = "magenta"
            elif "yellow" in name.lower():
                perf_type = "yellow"
            else:
                perf_type = "other"

            perfdata = [("supply_toner_" + perf_type, supply_level, warn, crit, 0, 100)]

            return state, infotext, perfdata
    return None


check_info["printer_supply_ricoh"] = LegacyCheckDefinition(
    name="printer_supply_ricoh",
    detect=equals(".1.3.6.1.2.1.1.2.0", ".1.3.6.1.4.1.367.1.1"),
    fetch=SNMPTree(
        base=".1.3.6.1.4.1.367.3.2.1.2.24.1.1",
        oids=["2", "5"],
    ),
    parse_function=parse_printer_supply_ricoh,
    service_name="Supply %s",
    discovery_function=discover_printer_supply_ricoh,
    check_function=check_printer_supply_ricoh,
    check_ruleset_name="printer_supply",
    check_default_parameters={"levels": (20.0, 10.0)},
)
