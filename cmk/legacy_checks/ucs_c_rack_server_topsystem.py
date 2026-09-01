#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# exemplary output of the special agent ucs_bladecenter (separator is <TAB> and means tabulator):
#
# <<<ucsc_topsystem:sep(9)>>>
# topSystem<TAB>dn sys<TAB>address 192.168.1.1<TAB>currentTime Wed Feb  6 09:12:12 2019<TAB>mode stand-alone<TAB>name CIMC-istreamer2a-etn


import time
from collections.abc import Sequence

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

type Section = Sequence[tuple[str, str]]


def parse_ucs_c_rack_server_topsystem(string_table: StringTable) -> Section:
    """
    Input: Single line string_table with a rack server topsystem information.
    Output: Returns the dn, address, current time, mode and name as title/value pairs.
    """
    parsed = []
    # The element count of string_table lines is under our control (agent output) and
    # ensured to have expected length. It is ensured that elements contain a
    # string. No bad case handling required here.
    for _, dn, ip, date_and_time, mode, name in string_table:
        # If more than one string_table line given or in case of unexpected string_table list
        # element format the parsed list will be empty.
        parsed.extend(
            [
                ("DN", dn.replace("dn ", "")),
                ("IP", ip.replace("address ", "")),
                ("Mode", mode.replace("mode ", "")),
                ("Name", name.replace("name ", "")),
            ]
        )
        parsed.append(("Date and time", _format_date_and_time(date_and_time)))
    return parsed


def discover_ucs_c_rack_server_topsystem(section: Section) -> DiscoveryResult:
    if section:
        yield Service()


def check_ucs_c_rack_server_topsystem(section: Section) -> CheckResult:
    for title, value in section:
        yield Result(state=State.OK, summary=f"{title}: {value}")


def _format_date_and_time(date_and_time: str) -> str:
    """Convert the reported date and time, e.g. Wed Feb  6 09:12:12 2019 -> 2019-02-06 09:12:12"""
    raw_value = date_and_time.replace("currentTime ", "")
    try:
        struct_time = time.strptime(raw_value[4:], "%b %d %H:%M:%S %Y")
    except ValueError:
        # indicate date and time format not supported
        return "unknown[%s]" % date_and_time[4:]
    return time.strftime("%Y-%m-%d %H:%M:%S", struct_time)


agent_section_ucs_c_rack_server_topsystem = AgentSection(
    name="ucs_c_rack_server_topsystem",
    parse_function=parse_ucs_c_rack_server_topsystem,
)


check_plugin_ucs_c_rack_server_topsystem = CheckPlugin(
    name="ucs_c_rack_server_topsystem",
    service_name="UCS C-Series Rack Server TopSystem Info",
    discovery_function=discover_ucs_c_rack_server_topsystem,
    check_function=check_ucs_c_rack_server_topsystem,
)
