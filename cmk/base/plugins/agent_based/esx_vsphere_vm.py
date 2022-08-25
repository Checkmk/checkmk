#!/usr/bin/env python3
# Copyright (C) 2022 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
from typing import Dict, List, Mapping, Sequence

from .agent_based_api.v1 import HostLabel, register
from .agent_based_api.v1.type_defs import StringTable
from .utils.esx_vsphere import ESXMemory, ESXVm, SectionVM


def parse_esx_vsphere_vm(string_table: StringTable) -> SectionVM:
    grouped_values: Dict[str, List[str]] = {}
    for line in string_table:
        # Do not monitor VM templates
        if line[0] == "config.template" and line[1] == "true":
            return None
        grouped_values[line[0]] = line[1:]

    return ESXVm(
        snapshots=grouped_values.get("snapshot.rootSnapshotList", []),
        power_state=_parse_esx_power_state(grouped_values),
        memory=_parse_esx_memory_section(grouped_values),
    )


def _parse_esx_power_state(vm_values: Mapping[str, Sequence[str]]) -> str | None:
    if "runtime.powerState" not in vm_values:
        return None
    return vm_values["runtime.powerState"][0]


def _parse_esx_memory_section(vm_values: Mapping[str, Sequence[str]]) -> ESXMemory | None:
    """Parse memory specific values from ESX VSphere VM agent output"""
    memory_mapping = {
        "hostMemoryUsage": "host_usage",
        "guestMemoryUsage": "guest_usage",
        "balloonedMemory": "ballooned",
        "sharedMemory": "shared",
        "privateMemory": "private",
    }

    memory_values = {}
    for memory_type in memory_mapping:
        try:
            value = float(vm_values[f"summary.quickStats.{memory_type}"][0])
        except (KeyError, TypeError, ValueError):
            return None

        memory_values[memory_mapping[memory_type]] = value * 1024**2
    return ESXMemory(**memory_values)


def host_label_esx_vshpere_vm(section):
    if "runtime.host" in section:
        yield HostLabel("cmk/vsphere_object", "vm")


register.agent_section(
    name="esx_vsphere_vm",
    parse_function=parse_esx_vsphere_vm,
    host_label_function=host_label_esx_vshpere_vm,
)
