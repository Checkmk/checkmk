#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

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

Section = Mapping[str, list[list[str]]]


def parse_jolokia_info(string_table: StringTable) -> Section:
    parsed: dict[str, list[list[str]]] = {}
    for line in string_table:
        parsed.setdefault(line[0], []).append(line[1:])
    return parsed


def check_jolokia_info(item: str, section: Section) -> CheckResult:
    if not (data := section.get(item)):
        return
    line = data[0]
    # Inform user of non-working agent plugin, eg. missing json library
    if item == "Error:":
        yield Result(state=State.UNKNOWN, summary=" ".join(line))
        return

    if line[0] == "ERROR" or len(line) < 3:
        yield Result(state=State.CRIT, summary=" ".join(line) or "Unknown error in plug-in")
        return

    product = line[0]
    jolokia_version = line[-1]
    version = " ".join(line[1:-1])
    yield Result(
        state=State.OK, summary=f"{product.title()} {version} (Jolokia version {jolokia_version})"
    )


def discover_jolokia_info(section: Section) -> DiscoveryResult:
    yield from (Service(item=item) for item in section)


agent_section_jolokia_info = AgentSection(
    name="jolokia_info",
    parse_function=parse_jolokia_info,
)


check_plugin_jolokia_info = CheckPlugin(
    name="jolokia_info",
    service_name="JVM %s",
    discovery_function=discover_jolokia_info,
    check_function=check_jolokia_info,
)
