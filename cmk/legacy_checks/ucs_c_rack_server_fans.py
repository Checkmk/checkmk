#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# exemplary agent output (separator is <TAB> and is tabulator):
# <<<ucs_c_rack_server_fans:sep(9)>>>
# equipmentFan<TAB>dn sys/rack-unit-1/fan-module-1-1/fan-1<TAB>id 1<TAB>model <TAB>operability operable


from collections.abc import Mapping

from cmk.agent_based.v2 import (
    AgentSection,
    CheckPlugin,
    CheckResult,
    DiscoveryResult,
    Result,
    Service,
    State,
    StringTable,
)

type Section = Mapping[str, str]

_OPERABILITY_TO_STATE = {
    "unknown": State.UNKNOWN,
    "operable": State.OK,
    "inoperable": State.CRIT,
}


def parse_ucs_c_rack_server_fans(string_table: StringTable) -> Section:
    parsed = {}

    for fan in string_table:
        try:
            key_value_pairs = [kv.split(" ", 1) for kv in fan[1:]]
            item = (
                key_value_pairs[0][1]
                .replace("sys/", "")
                .replace("rack-unit-", "Rack Unit ")
                .replace("/fan-module-", " Module ")
                .replace("/fan-", " ")
            )
            parsed[item] = key_value_pairs[3][1]
        except IndexError, ValueError:
            pass

    return parsed


def discover_ucs_c_rack_server_fans(section: Section) -> DiscoveryResult:
    yield from (Service(item=item) for item in section)


def check_ucs_c_rack_server_fans(item: str, section: Section) -> CheckResult:
    if (operability := section.get(item)) is None:
        return

    if (state := _OPERABILITY_TO_STATE.get(operability)) is None:
        yield Result(state=State.UNKNOWN, summary=f"Unknown Operability Status: {operability}")
    else:
        yield Result(state=state, summary=f"Operability Status is {operability}")


agent_section_ucs_c_rack_server_fans = AgentSection(
    name="ucs_c_rack_server_fans",
    parse_function=parse_ucs_c_rack_server_fans,
)


check_plugin_ucs_c_rack_server_fans = CheckPlugin(
    name="ucs_c_rack_server_fans",
    service_name="Fan %s",
    discovery_function=discover_ucs_c_rack_server_fans,
    check_function=check_ucs_c_rack_server_fans,
)
