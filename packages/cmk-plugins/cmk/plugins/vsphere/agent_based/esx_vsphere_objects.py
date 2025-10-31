#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# Example output from agent:
# <<<esx_vsphere_objects:sep(9)>>>
# hostsystem  esx.wacker.corp
# virtualmachine  LinuxI
# virtualmachine  OpenSUSE_II
# virtualmachine  OpenSUSE_III
# virtualmachine  OpenSUSE_IV
# virtualmachine  OpenSUSE_V
# virtualmachine  WindowsXP I
# virtualmachine  LinuxII
# virtualmachine  LinuxIII
# virtualmachine  LinuxIV
# virtualmachine  LinuxV
# virtualmachine  OpenSUSE_I

from itertools import chain

from cmk.agent_based.v2 import (
    AgentSection,
    CheckPlugin,
    CheckResult,
    DiscoveryResult,
    Metric,
    Result,
    Service,
    State,
    StringTable,
)
from cmk.plugins.vsphere.lib.esx_vsphere_objects import (
    ObjectCountParamsMapping,
    ObjectDiscoveryParams,
    ParsedSection,
    StateParams,
    StateParamsMapping,
    VmInfo,
    VSPHERE_OBJECT_NAMES,
)


def parse_esx_vsphere_objects(string_table: StringTable) -> ParsedSection:
    parsed = {}
    for line in string_table:
        if len(line) < 2:
            continue
        if len(line) < 4:
            line += [""] * (4 - len(line))
        vm_info = VmInfo(
            name=line[1],
            vmtype=VSPHERE_OBJECT_NAMES.get(line[0], "Unknown Object"),
            hostsystem=line[2],
            state=line[3],
        )
        parsed[vm_info.service_name] = vm_info

    return parsed


#   .--Single--------------------------------------------------------------.
#   |                     ____  _             _                            |
#   |                    / ___|(_)_ __   __ _| | ___                       |
#   |                    \___ \| | '_ \ / _` | |/ _ \                      |
#   |                     ___) | | | | | (_| | |  __/                      |
#   |                    |____/|_|_| |_|\__, |_|\___|                      |
#   |                                   |___/                              |
#   '----------------------------------------------------------------------'


def discovery_esx_vsphere_objects(
    params: ObjectDiscoveryParams, section: ParsedSection
) -> DiscoveryResult:
    for key, vm_info in section.items():
        if vm_info.vmtype != "Template" or params["templates"]:
            yield Service(item=key)


def check_esx_vsphere_objects(
    item: str, params: StateParamsMapping, section: ParsedSection
) -> CheckResult:
    obj = section.get(item)
    if obj is None:
        yield Result(state=State.UNKNOWN, summary=f"Missing item: {item}")
        return

    if not obj.state:
        yield Result(state=State.CRIT, summary=f"No data about {obj.service_name}")
        return

    if obj.vmtype == "Template":
        # Templates cannot be powered on, so the state is always OK.
        state = State.OK
    else:
        state = State(params["states"].get(obj.state, 3))
    yield Result(state=state, summary=f"power state: {obj.state}")

    if obj.hostsystem:
        if obj.state == "poweredOn":
            yield Result(state=State.OK, summary=f"running on [{obj.hostsystem}]")
        else:
            yield Result(state=State.OK, summary=f"defined on [{obj.hostsystem}]")


agent_section_esx_vsphere_objects = AgentSection(
    name="esx_vsphere_objects",
    parse_function=parse_esx_vsphere_objects,
)


check_plugin_esx_vsphere_objects = CheckPlugin(
    name="esx_vsphere_objects",
    service_name="%s",
    discovery_function=discovery_esx_vsphere_objects,
    discovery_ruleset_name="esx_vsphere_objects_discovery",
    discovery_default_parameters={"templates": True},
    check_function=check_esx_vsphere_objects,
    check_ruleset_name="esx_vsphere_objects",
    check_default_parameters={
        "states": StateParams(
            poweredOn=0,
            standBy=1,
            poweredOff=1,
            suspended=1,
            unknown=3,
        )
    },
)


def discovery_esx_vsphere_objects_count(section: ParsedSection) -> DiscoveryResult:
    yield Service()


def check_esx_vsphere_objects_count(
    params: ObjectCountParamsMapping, section: ParsedSection
) -> CheckResult:
    templates = [o for o in section.values() if o.vmtype == "Template"]
    yield Result(state=State.OK, summary=f"Templates: {len(templates)}")
    yield Metric(name="templates", value=len(templates))

    virtualmachines = [o for o in section.values() if o.vmtype == "VM"]
    yield Result(state=State.OK, summary=f"Virtualmachines: {len(virtualmachines)}")
    yield Metric(name="vms", value=len(virtualmachines))

    hostsystems = [o for o in section.values() if o.vmtype == "HostSystem"]
    if not hostsystems:
        return

    yield Result(state=State.OK, summary=f"Hostsystems: {len(hostsystems)}")
    yield Metric(name="hosts", value=len(hostsystems))

    for distribution in params["distribution"]:
        ruled_vms = distribution["vm_names"]
        hosts = sorted(
            {vm.hostsystem for vm in chain(virtualmachines, templates) if vm.name in ruled_vms}
        )
        count = len(hosts)
        if count < distribution["hosts_count"]:
            yield Result(
                state=State(distribution["state"]),
                summary=(
                    f"VMs {', '.join(ruled_vms)} are running on {count} "
                    f"host{'' if count == 1 else 's'}: {', '.join(hosts)}"
                ),
            )


check_plugin_esx_vsphere_objects_count = CheckPlugin(
    name="esx_vsphere_objects_count",
    service_name="Object count",
    sections=["esx_vsphere_objects"],
    discovery_function=discovery_esx_vsphere_objects_count,
    check_function=check_esx_vsphere_objects_count,
    check_ruleset_name="esx_vsphere_objects_count",
    check_default_parameters={
        "distribution": [],
    },
)
