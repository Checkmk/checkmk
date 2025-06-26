#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# Thanks to Andreas Döhler for the contribution.

from collections.abc import Mapping
from typing import Any

from cmk.agent_based.v2 import (
    StringTable,
)

Section = Mapping[str, Mapping[str, Any]]


def hyperv_vm_convert(string_table: StringTable) -> Mapping[str, str]:
    parsed: dict[str, str] = {}
    for line in string_table:
        parsed[line[0]] = " ".join(line[1:])

    return parsed


COUNTER_TRANSLATIONS = {
    "durchschnittl. warteschlangenlänge der datenträger-lesevorgänge": "avg. disk read queue length",
    "durchschnittl. warteschlangenlänge der datenträger-schreibvorgänge": "avg. disk write queue length",
    "mittlere sek./lesevorgänge": "avg. disk sec/read",
    "mittlere sek./schreibvorgänge": "avg. disk sec/write",
    "lesevorgänge/s": "disk reads/sec",
    "schreibvorgänge/s": "disk writes/sec",
    "bytes gelesen/s": "disk read bytes/sec",
    "bytes geschrieben/s": "disk write bytes/sec",
}


def parse_hyperv_io(string_table: StringTable) -> Section:
    parsed: dict[str, Any] = {}
    for line in string_table:
        value = line[-1]
        data = " ".join(line[:-1])
        _empty, _empty2, host, lun, name = data.split("\\", 4)
        name = COUNTER_TRANSLATIONS.get(name, name)
        lun_data = parsed.setdefault(lun, {})
        lun_data[name] = value
        lun_data["node"] = host
    return parsed


def parse_hyperv(string_table: StringTable) -> Section:
    datatypes = {
        "vhd": "vhd.name",
        "nic": "nic.name",
        "checkpoints": "checkpoint.name",
        "cluster.number_of_nodes": "cluster.node.name",
        "cluster.number_of_csv": "cluster.csv.name",
        "cluster.number_of_disks": "cluster.disk.name",
        "cluster.number_of_vms": "cluster.vm.name",
        "cluster.number_of_roles": "cluster.role.name",
        "cluster.number_of_networks": "cluster.network.name",
    }

    parsed: dict[str, dict[str, Any]] = {}
    if len(string_table) == 0:
        return parsed

    datatype = datatypes.get(string_table[0][0])
    element = ""
    start = False
    counter = 1
    for line in string_table:
        if line[0] == datatype:
            if start:
                counter += 1
            else:
                start = True

            if datatype == "nic.name":
                element = f"{' '.join(line[1:])} {counter}"
            else:
                element = f"{' '.join(line[1:])}"

            parsed[element] = {}  # The potential reset was suggested and works with the given
        # set of examples but the logic should be revisited (CMK-24315)

        elif start:
            element_data = parsed.setdefault(element, {})
            element_data[line[0]] = " ".join(line[1:])

    return parsed
