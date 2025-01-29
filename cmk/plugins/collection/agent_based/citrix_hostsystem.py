#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# Example output from agent:
# <<<citrix_hostsystem>>>
# VMName rz1css01
# CitrixPoolName RZ1XenPool01 - Cisco UCS


# Note(1): The pool name is the same for all VMs on one host system
# Note(2): for the same host and vm this section can appear
# several times (with the same content).


from typing import TypedDict

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


class Section(TypedDict):
    vms: tuple[str, ...]
    pool: str


def parse_citrix_hostsystem(string_table: StringTable) -> Section:
    vms = []
    pool = ""
    for line in string_table:
        if line[0] == "VMName":
            vm = " ".join(line[1:])
            if vm not in vms:
                vms.append(vm)
        elif line[0] == "CitrixPoolName":
            pool = pool or " ".join(line[1:])

    return {"vms": tuple(vms), "pool": pool}


#   .--Host VMs------------------------------------------------------------.
#   |              _   _           _    __     ____  __                    |
#   |             | | | | ___  ___| |_  \ \   / /  \/  |___                |
#   |             | |_| |/ _ \/ __| __|  \ \ / /| |\/| / __|               |
#   |             |  _  | (_) \__ \ |_    \ V / | |  | \__ \               |
#   |             |_| |_|\___/|___/\__|    \_/  |_|  |_|___/               |
#   |                                                                      |
#   '----------------------------------------------------------------------'


def inventory_citrix_hostsystem_vms(section: Section) -> DiscoveryResult:
    if section["vms"]:
        yield Service()


def check_citrix_hostsystem_vms(section: Section) -> CheckResult:
    vmlist = section["vms"]
    yield Result(state=State.OK, summary="%d VMs running: %s" % (len(vmlist), ", ".join(vmlist)))


check_plugin_citrix_hostsystem_vms = CheckPlugin(
    name="citrix_hostsystem_vms",
    service_name="Citrix VMs",
    sections=["citrix_hostsystem"],
    discovery_function=inventory_citrix_hostsystem_vms,
    check_function=check_citrix_hostsystem_vms,
)

# .
#   .--Host Info-----------------------------------------------------------.
#   |              _   _           _     ___        __                     |
#   |             | | | | ___  ___| |_  |_ _|_ __  / _| ___                |
#   |             | |_| |/ _ \/ __| __|  | || '_ \| |_ / _ \               |
#   |             |  _  | (_) \__ \ |_   | || | | |  _| (_) |              |
#   |             |_| |_|\___/|___/\__| |___|_| |_|_|  \___/               |
#   |                                                                      |
#   '----------------------------------------------------------------------'


def inventory_citrix_hostsystem(section: Section) -> DiscoveryResult:
    if section["pool"]:
        yield Service()


def check_citrix_hostsystem(section: Section) -> CheckResult:
    yield Result(state=State.OK, summary="Citrix Pool Name: %s" % section["pool"])


agent_section_citrix_hostsystem = AgentSection(
    name="citrix_hostsystem", parse_function=parse_citrix_hostsystem
)


check_plugin_citrix_hostsystem = CheckPlugin(
    name="citrix_hostsystem",
    service_name="Citrix Host Info",
    discovery_function=inventory_citrix_hostsystem,
    check_function=check_citrix_hostsystem,
)
