#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import json
from collections.abc import Sequence
from typing import TypedDict

from cmk.agent_based.v2 import AgentSection, InventoryPlugin, InventoryResult, StringTable, TableRow


class VM(TypedDict):
    vm_name: str
    hostsystem: str
    powerstate: str
    guest_os: str
    compatibility: str
    uuid: str


Section = Sequence[VM]


def parse_esx_vsphere_virtual_machines(string_table: StringTable) -> Section:
    return [json.loads(vm_json[0]) for vm_json in string_table]


agent_section_esx_vsphere_virtual_machines = AgentSection(
    name="esx_vsphere_virtual_machines",
    parse_function=parse_esx_vsphere_virtual_machines,
)


def inventory_esx_vsphere_virtual_machines(section: Section) -> InventoryResult:
    for vm in section:
        yield TableRow(
            path=["software", "virtual_machines"],
            key_columns={"uuid": vm["uuid"]},
            inventory_columns={
                "hostsystem": vm["hostsystem"],
                "vm_name": vm["vm_name"],
                "guest_os": vm["guest_os"],
                "compatibility": vm["compatibility"],
            },
        )


inventory_plugin_inventory_esx_vsphere_virtual_machines = InventoryPlugin(
    name="inventory_esx_vsphere_virtual_machines",
    sections=["esx_vsphere_virtual_machines"],
    inventory_function=inventory_esx_vsphere_virtual_machines,
)
