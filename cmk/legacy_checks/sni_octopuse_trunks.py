#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# .1.3.6.1.4.1.231.7.2.9.3.8.1.3.1  "OpenStage 30"
# .1.3.6.1.4.1.231.7.2.9.3.8.1.3.2  "OpenStage 30"
# .1.3.6.1.4.1.231.7.2.9.3.8.1.3.7  "P. O. T."
# .1.3.6.1.4.1.231.7.2.9.3.8.1.3.9  "S0 extension"
# .1.3.6.1.4.1.231.7.2.9.3.8.1.3.11  "S0 trunk: extern"
# .1.3.6.1.4.1.231.7.2.9.3.8.1.3.13  "<not configured>: extern"
# [...]
# .1.3.6.1.4.1.231.7.2.9.3.8.1.4.11  2
# .1.3.6.1.4.1.231.7.2.9.3.8.1.4.13  1


from collections.abc import Sequence

from cmk.agent_based.v2 import (
    CheckPlugin,
    CheckResult,
    DiscoveryResult,
    Result,
    Service,
    SNMPSection,
    SNMPTree,
    State,
    StringTable,
)
from cmk.plugins.sni_octopuse.lib import DETECT_SNI_OCTOPUSE

_TRUNKPORTS = ("S0 trunk: extern",)


def discover_octopus_trunks(section: Sequence[StringTable]) -> DiscoveryResult:
    for line in section[0]:
        if len(line) == 4:
            portindex, cardindex, porttype, portstate = line
            if porttype in _TRUNKPORTS and portstate == "2":
                yield Service(item=f"{cardindex}/{portindex}")


def check_octopus_trunks(item: str, section: Sequence[StringTable]) -> CheckResult:
    for line in section[0]:
        portindex, cardindex, porttype, portstate = line
        if item == f"{cardindex}/{portindex}":
            # There are two relevant card states, we use the one from
            # octoPortTable
            if portstate == "1":
                yield Result(state=State.CRIT, summary=f"Port [{porttype}] is inactive")
                return
            yield Result(state=State.OK, summary=f"Port [{porttype}] is active")
            return

    yield Result(state=State.UNKNOWN, summary="UNKW - unknown data received from agent")


def parse_sni_octopuse_trunks(string_table: Sequence[StringTable]) -> Sequence[StringTable]:
    return string_table


snmp_section_sni_octopuse_trunks = SNMPSection(
    name="sni_octopuse_trunks",
    detect=DETECT_SNI_OCTOPUSE,
    fetch=[
        SNMPTree(
            base=".1.3.6.1.4.1.231.7.2.9.3.8.1",
            oids=["1", "2", "3", "4"],
        )
    ],
    parse_function=parse_sni_octopuse_trunks,
)


check_plugin_sni_octopuse_trunks = CheckPlugin(
    name="sni_octopuse_trunks",
    service_name="Trunk Port %s",
    discovery_function=discover_octopus_trunks,
    check_function=check_octopus_trunks,
)
