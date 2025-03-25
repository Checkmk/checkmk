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


import collections

from cmk.agent_based.legacy.v0_unstable import LegacyCheckDefinition

check_info = {}

vsphere_object_names = {
    "hostsystem": "HostSystem",
    "virtualmachine": "VM",
}


def parse_esx_vsphere_objects(string_table):
    parsed = {}
    Obj = collections.namedtuple(  # nosemgrep: typing-namedtuple-call
        "Obj", ["name", "hostsystem", "state"]
    )
    for line in string_table:
        if len(line) < 2:
            continue
        if len(line) < 4:
            line += [""] * (4 - len(line))
        obj_type = vsphere_object_names.get(line[0], "Unknown Object")
        name = f"{obj_type} {line[1]}"
        obj = Obj(name, line[2], line[3])
        parsed[obj.name] = obj

    return parsed


#   .--Single--------------------------------------------------------------.
#   |                     ____  _             _                            |
#   |                    / ___|(_)_ __   __ _| | ___                       |
#   |                    \___ \| | '_ \ / _` | |/ _ \                      |
#   |                     ___) | | | | | (_| | |  __/                      |
#   |                    |____/|_|_| |_|\__, |_|\___|                      |
#   |                                   |___/                              |
#   '----------------------------------------------------------------------'


def inventory_esx_vsphere_objects(parsed):
    for key in parsed:
        yield key, {}


def check_esx_vsphere_objects(item, params, parsed):
    if params is None:
        params = {}

    obj = parsed.get(item)
    if obj is None:
        yield 3, "Missing item: %s" % item
        return

    if not obj.state:
        what, name = item.split()
        if what == "VM":
            yield 3, "Virtual machine %s is missing" % name
        else:
            yield 3, "No data about host system %s" % name
        return

    state = params.get("states", {}).get(obj.state, 3)
    yield state, "power state: %s" % obj.state

    if obj.hostsystem:
        if obj.state == "poweredOn":
            yield 0, "running on [%s]" % obj.hostsystem
        else:
            yield 0, "defined on [%s]" % obj.hostsystem


check_info["esx_vsphere_objects"] = LegacyCheckDefinition(
    name="esx_vsphere_objects",
    parse_function=parse_esx_vsphere_objects,
    service_name="%s",
    discovery_function=inventory_esx_vsphere_objects,
    check_function=check_esx_vsphere_objects,
    check_ruleset_name="esx_vsphere_objects",
    check_default_parameters={
        "states": {
            "poweredOn": 0,
            "standBy": 1,
            "poweredOff": 1,
            "suspended": 1,
            "unknown": 3,
        }
    },
)


def inventory_esx_vsphere_objects_count(parsed):
    yield None, {}


def check_esx_vsphere_objects_count(_no_item, params, parsed):
    if params is None:
        params = {}

    virtualmachines = [o for o in parsed.values() if o.name.startswith("VM ")]
    yield 0, "Virtualmachines: %d" % len(virtualmachines), [("vms", len(virtualmachines))]

    hostsystems = [o for o in parsed.values() if o.name.startswith("HostSystem")]
    if not hostsystems:
        return

    yield 0, "Hostsystems: %d" % len(hostsystems), [("hosts", len(hostsystems))]

    for distribution in params.get("distribution", []):
        ruled_vms = distribution.get("vm_names", [])
        hosts = sorted({vm.hostsystem for vm in virtualmachines if vm.name[3:] in ruled_vms})
        count = len(hosts)
        if count < distribution["hosts_count"]:
            yield (
                distribution.get("state", 2),
                (
                    "VMs %s are running on %d host%s: %s"
                    % (", ".join(ruled_vms), count, "" if count == 1 else "s", ", ".join(hosts))
                ),
            )


check_info["esx_vsphere_objects.count"] = LegacyCheckDefinition(
    name="esx_vsphere_objects_count",
    service_name="Object count",
    sections=["esx_vsphere_objects"],
    discovery_function=inventory_esx_vsphere_objects_count,
    check_function=check_esx_vsphere_objects_count,
    check_ruleset_name="esx_vsphere_objects_count",
    check_default_parameters={
        "distribution": [],
    },
)
