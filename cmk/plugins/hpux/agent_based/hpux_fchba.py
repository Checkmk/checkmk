#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# <<<hpux_fchba>>>
# /dev/fcd0
#                        ISP Code version = 4.4.4
#                                Topology = PTTOPT_FABRIC
#             N_Port Port World Wide Name = 0x500143800252658a
#             Switch Port World Wide Name = 0x200400051e6302d7
#                            Driver state = ONLINE
#                        Hardware Path is = 0/0/1/1/0
#          Driver-Firmware Dump Available = NO
# /dev/fcd1
#                        ISP Code version = 4.4.4
#                                Topology = PTTOPT_FABRIC
#             N_Port Port World Wide Name = 0x500143800252658c
#             Switch Port World Wide Name = 0x200400051e5d1942
#                            Driver state = ONLINE
#                        Hardware Path is = 1/0/12/1/0
#          Driver-Firmware Dump Available = NO


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

Section = dict[str, dict[str, str]]


def parse_hpux_fchba(string_table: StringTable) -> Section:
    hbas: Section = {}
    hba: dict[str, str] = {}
    for line in string_table:
        if line[0].startswith("/dev/"):
            name = line[0][5:]
            hba = {"name": name}
            hbas[name] = hba
        elif len(line) == 2:
            hba[line[0].strip()] = line[1].strip()
    return hbas


def discover_hpux_fchba(section: Section) -> DiscoveryResult:
    for name, hba in section.items():
        if hba["Driver state"] == "ONLINE":
            yield Service(item=name)


def check_hpux_fchba(item: str, section: Section) -> CheckResult:
    if (hba := section.get(item)) is None:
        return

    state = State.OK
    infos = []

    infos.append(f"Hardware Path: {hba['Hardware Path is']}")

    infos.append(f"Driver State: {hba['Driver state']}")
    if hba["Driver state"] != "ONLINE":
        state = State.CRIT
        infos[-1] += "(!!)"

    infos.append(f"Topology: {hba.get('Topology', '(none)')}")
    if hba.get("Topology") not in [
        "PTTOPT_FABRIC",
        "PRIVATE_LOOP",
        "PUBLIC_LOOP",
    ]:
        state = State.CRIT
        infos[-1] += "(!!)"

    if hba.get("Driver-Firmware Dump Available", "NO") != "NO":
        infos.append("Driver-Firmware Dump Available(!!)")
        state = State.CRIT

    yield Result(state=state, summary=", ".join(infos))


agent_section_hpux_fchba = AgentSection(
    name="hpux_fchba",
    parse_function=parse_hpux_fchba,
)


check_plugin_hpux_fchba = CheckPlugin(
    name="hpux_fchba",
    service_name="FC HBA %s",
    discovery_function=discover_hpux_fchba,
    check_function=check_hpux_fchba,
)
