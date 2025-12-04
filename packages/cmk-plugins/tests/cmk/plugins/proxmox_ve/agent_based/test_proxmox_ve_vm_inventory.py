#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import pytest

from cmk.agent_based.v2 import Attributes, InventoryResult
from cmk.plugins.proxmox_ve.agent_based.proxmox_ve_vm_inventory import inventory_proxmox_ve_vm
from cmk.plugins.proxmox_ve.lib.vm_info import SectionVMInfo

SECTION_VM_INFO_QEMU = SectionVMInfo(
    vmid="133",
    node="pve-dc4-001",
    status="running",
    type="qemu",
    name="aq-test.lan.mathias-kettner.de",
    uptime=12345,
)

SECTION_VM_INFO_LXC = SectionVMInfo(
    vmid="133",
    node="pve-dc4-001",
    status="running",
    type="lxc",
    name="aq-test.lan.mathias-kettner.de",
    uptime=12345,
)


@pytest.mark.parametrize(
    "section_proxmox_ve_vm_info, expected_attributes",
    [
        pytest.param(
            SECTION_VM_INFO_QEMU,
            [
                Attributes(
                    path=["software", "applications", "proxmox_ve", "metadata"],
                    inventory_attributes={
                        "object": "VM",
                        "provider": "Proxmox VE",
                        "name": "aq-test.lan.mathias-kettner.de",
                        "node": "pve-dc4-001",
                    },
                    status_attributes={},
                ),
            ],
            id="QEMU VM",
        ),
        pytest.param(
            SECTION_VM_INFO_LXC,
            [
                Attributes(
                    path=["software", "applications", "proxmox_ve", "metadata"],
                    inventory_attributes={
                        "object": "LXC",
                        "provider": "Proxmox VE",
                        "name": "aq-test.lan.mathias-kettner.de",
                        "node": "pve-dc4-001",
                    },
                    status_attributes={},
                ),
            ],
            id="LXC Container",
        ),
    ],
)
def test_inventory_proxmox_ve_vm(
    section_proxmox_ve_vm_info: SectionVMInfo, expected_attributes: InventoryResult
) -> None:
    assert list(inventory_proxmox_ve_vm(section=section_proxmox_ve_vm_info)) == expected_attributes
