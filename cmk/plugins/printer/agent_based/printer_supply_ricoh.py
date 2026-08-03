#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# mypy: disable-error-code="explicit-any"

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

from cmk.agent_based.v2 import (
    CheckPlugin,
    CheckResult,
    DiscoveryResult,
    equals,
    Metric,
    Result,
    Service,
    SimpleSNMPSection,
    SNMPTree,
    State,
    StringTable,
)

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


def discover_printer_supply_ricoh(section: Section) -> DiscoveryResult:
    for key in section:
        yield Service(item=key)


def check_printer_supply_ricoh(
    item: str, params: Mapping[str, Any] | tuple[float, ...], section: Section
) -> CheckResult:
    def handle_regular(supply_level: int) -> tuple[State, str, int]:
        infotext = f"{supply_level:.0f}%"

        if supply_level <= crit:
            state = State.CRIT
        elif supply_level <= warn:
            state = State.WARN
        else:
            state = State.OK

        if state != State.OK:
            infotext += f" (warn/crit at {warn:.0f}%/{crit:.0f}%)"
        return state, infotext, supply_level

    def handle_negative(code: int) -> tuple[State, str, int]:
        # the following codes are based on the MP C2800
        if code == -100:
            # does not apply level. Since we don't get a proper reading
            # the best we could do would be test against 0
            return State.CRIT, "almost empty (<10%)", 0
        if code == -2:
            # cartridge removed?
            return State.UNKNOWN, "unknown level", 0
        if code == -3:
            # -3 = full is based on user claim, but other walks also show
            # the device itself does not alert in this state
            return State.OK, "100%", 100
        # unknown code
        return handle_regular(0)

    if isinstance(params, tuple):
        if len(params) == 2:
            params = {"levels": params}
        else:
            params = {"levels": params[:2], "upturn_toner": params[2]}

    warn, crit = params["levels"]
    if item not in section:
        return

    supply_level = section[item]
    if supply_level < 0:
        # negative levels usually have special meaning
        state, infotext, supply_level = handle_negative(supply_level)
    else:
        state, infotext, supply_level = handle_regular(supply_level)

    if "black" in item.lower():
        perf_type = "black"
    elif "cyan" in item.lower():
        perf_type = "cyan"
    elif "magenta" in item.lower():
        perf_type = "magenta"
    elif "yellow" in item.lower():
        perf_type = "yellow"
    else:
        perf_type = "other"

    yield Result(state=state, summary=infotext)
    yield Metric(
        f"supply_toner_{perf_type}", supply_level, levels=(warn, crit), boundaries=(0, 100)
    )


snmp_section_printer_supply_ricoh = SimpleSNMPSection(
    name="printer_supply_ricoh",
    detect=equals(".1.3.6.1.2.1.1.2.0", ".1.3.6.1.4.1.367.1.1"),
    fetch=SNMPTree(
        base=".1.3.6.1.4.1.367.3.2.1.2.24.1.1",
        oids=["2", "5"],
    ),
    parse_function=parse_printer_supply_ricoh,
)


check_plugin_printer_supply_ricoh = CheckPlugin(
    name="printer_supply_ricoh",
    service_name="Supply %s",
    discovery_function=discover_printer_supply_ricoh,
    check_function=check_printer_supply_ricoh,
    check_ruleset_name="printer_supply",
    check_default_parameters={"levels": (20.0, 10.0)},
)
