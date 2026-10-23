#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import json

from cmk.agent_based.v2 import TableRow
from cmk.plugins.vsphere.agent_based.inventory_esx_vsphere_virtual_machines import (
    inventorize_esx_vsphere_virtual_machines,
    parse_esx_vsphere_virtual_machines,
    VM,
)

WEB_01 = VM(
    vm_name="web-01",
    hostsystem="esx01.example.com",
    powerstate="poweredOn",
    guest_os="Ubuntu Linux (64-bit)",
    compatibility="vmx-19",
    uuid="4213a1b2-0000-4000-8000-000000000001",
)


def test_each_json_line_becomes_one_vm_record() -> None:
    section = parse_esx_vsphere_virtual_machines([[json.dumps(WEB_01)]])

    assert section == [WEB_01]


def test_each_vm_becomes_one_inventory_row_keyed_by_its_uuid() -> None:
    (row,) = inventorize_esx_vsphere_virtual_machines([WEB_01])

    assert isinstance(row, TableRow)
    assert row.path == ["software", "virtual_machines"]
    assert row.key_columns == {"uuid": WEB_01["uuid"]}
    assert row.inventory_columns == {
        "hostsystem": "esx01.example.com",
        "vm_name": "web-01",
        "guest_os": "Ubuntu Linux (64-bit)",
        "compatibility": "vmx-19",
    }
