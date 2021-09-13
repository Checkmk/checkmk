#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# Example output:
# hardware.pciDevice.deviceName.00:00.0 5520 I/O Hub to ESI Port
# hardware.pciDevice.deviceName.00:01.0 5520/5500/X58 I/O Hub PCI Express Root Port 1
# hardware.pciDevice.deviceName.00:02.0 5520/5500/X58 I/O Hub PCI Express Root Port 2
# hardware.pciDevice.deviceName.00:03.0 5520/5500/X58 I/O Hub PCI Express Root Port 3
# hardware.cpuPkg.busHz.0 133338028
# hardware.cpuPkg.busHz.1 133338066
# hardware.cpuPkg.description.0 Intel(R) Xeon(R) CPU           X5670  @ 2.93GHz
# hardware.cpuPkg.description.1 Intel(R) Xeon(R) CPU           X5670  @ 2.93GHz
# hardware.cpuPkg.hz.0 2933437438
# hardware.cpuPkg.hz.1 2933437797
# hardware.cpuPkg.index.0 0
# hardware.cpuPkg.index.1 1
# hardware.cpuPkg.vendor.0 intel
# hardware.cpuPkg.vendor.1 intel

import time
from typing import Callable, Dict, Final, List, Optional, Tuple, TypedDict, Union

from .agent_based_api.v1 import Attributes, register, type_defs
from .utils.esx_vsphere import Section

FIRST_ELEMENT: Final = lambda v: v[0]
FIRST_ELEMENT_AS_FLOAT: Final = lambda v: float(v[0])
JOIN_LIST: Final = " ".join
SUB_SECTION = TypedDict(
    "SUB_SECTION", {"path": List[str], "translation": Dict[str, Tuple[str, Callable]]}
)

# This giant dict describes how the section translates into the different nodes of the inventory
SECTION_TO_INVENTORY: Dict[str, SUB_SECTION] = {
    "hw": {
        "path": ["hardware", "cpu"],
        "translation": {
            "hardware.cpuInfo.hz": ("max_speed", FIRST_ELEMENT_AS_FLOAT),
            "hardware.cpuInfo.numCpuPackages": ("cpus", FIRST_ELEMENT),
            "hardware.cpuInfo.numCpuCores": ("cores", FIRST_ELEMENT),
            "hardware.cpuInfo.numCpuThreads": ("threads", FIRST_ELEMENT),
            "hardware.cpuPkg.description.1": ("model", JOIN_LIST),
            "hardware.cpuPkg.vendor.1": ("vendor", FIRST_ELEMENT),
            "hardware.cpuPkg.busHz.0": ("bus_speed", FIRST_ELEMENT_AS_FLOAT),
        },
    },
    "sw": {
        "path": ["software", "bios"],
        "translation": {
            "hardware.biosInfo.biosVersion": ("version", FIRST_ELEMENT),
            "hardware.biosInfo.releaseDate": ("date", lambda v: _try_convert_to_epoch(v[0])),
        },
    },
    "sys": {
        "path": ["hardware", "system"],
        "translation": {
            "hardware.systemInfo.model": ("product", JOIN_LIST),
            "hardware.systemInfo.vendor": ("vendor", FIRST_ELEMENT),
            "hardware.systemInfo.uuid": ("uuid", FIRST_ELEMENT),
            "hardware.systemInfo.0.ServiceTag": ("serial", FIRST_ELEMENT),
        },
    },
    "mem": {
        "path": ["hardware", "memory"],
        "translation": {"hardware.memorySize": ("total_ram_usable", FIRST_ELEMENT_AS_FLOAT)},
    },
}


def _try_convert_to_epoch(release_date: str) -> Optional[str]:
    try:
        epoch = time.strftime("%Y-%m-%d", time.strptime(release_date, "%Y-%m-%dT%H:%M:%SZ"))
    except ValueError:
        return None
    return epoch


def inv_esx_vsphere_hostsystem(section: Section) -> type_defs.InventoryResult:

    for name, sub_section in SECTION_TO_INVENTORY.items():
        data: Dict[str, Union[None, str, float]] = {}
        for section_key, (inv_key, transform) in sub_section["translation"].items():
            if section_key in section:
                # Found after update to 2.9.0. Seems to be a false positive
                data[inv_key] = transform(section[section_key])  # pylint: disable=not-callable

        # Handle some corner cases for hw and sys
        if name == "hw":
            if all(k in data for k in ["cpus", "cores", "threads"]):
                for inv_key, metric in (("cores_per_cpu", "cores"), ("threads_per_cpu", "threads")):
                    data[inv_key] = int(data[metric]) / int(data["cpus"])  # type: ignore[arg-type]
        if name == "sys":
            # We only know for HP that ServiceTag is the serial...
            if data["vendor"] == "HP":
                # ...but it is missing in some cases
                try:
                    data["serial"] = section[
                        "hardware.systemInfo.otherIdentifyingInfo.ServiceTag.0"
                    ][0]
                except KeyError:
                    pass

        yield Attributes(path=sub_section["path"], inventory_attributes=data)


register.inventory_plugin(
    name="inv_esx_vsphere_hostsystem",
    sections=["esx_vsphere_hostsystem"],
    inventory_function=inv_esx_vsphere_hostsystem,
)
