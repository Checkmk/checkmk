#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# Example output from agent:
# <<<hyperv_vm_nic:cached(1750083965,120)>>>
# nic 1
# nic.name Network Adapter
# nic.id Microsoft:12345678-1234-1234-1234-123456789ABC\98765432-9876-9876-9876-987654321DEF
# nic.connectionstate True
# nic.vswitch Red Hat VirtIO Ethernet Adapter - Virtual Switch
# nic.dynamicMAC True
# nic.MAC 3E5A9C7F2B1D
# nic.IP 192.168.122.13
# nic.IP fe80::1a2b:3c4d:5e6f:7g8h
# nic.security.DHCPGuard Off
# nic.security.RouterGuard Off
# nic.VLAN.mode Untagged
# nic.VLAN.id 0


from collections.abc import Mapping

import pytest

from cmk.agent_based.v2 import Result, Service, State
from cmk.plugins.hyperv_cluster.agent_based.hyperv_vm_nic import (
    check_hyperv_vm_nic,
    discovery_hyperv_vm_nic,
)

test_section: Mapping[str, Mapping[str, str]] = {
    "NIC1": {
        "nic.connectionstate": "True",
        "nic.vswitch": "vSwitch1",
        "nic.VLAN.id": "100",
    },
    "NIC2": {
        "nic.connectionstate": "False",
        "nic.vswitch": "vSwitch2",
        "nic.VLAN.id": "200",
    },
}


def test_discovery_hyperv_vm_nic():
    result = list(discovery_hyperv_vm_nic(test_section))
    assert result == [Service(item="NIC1"), Service(item="NIC2")]


@pytest.mark.parametrize(
    "item, expected_state, expected_summary",
    [
        ("NIC1", State.OK, "NIC1 connected to vSwitch1 with VLAN ID 100"),
        ("NIC2", State.WARN, "NIC2 disconnected"),
        ("NIC3", State.OK, "NIC information is missing"),
    ],
)
def test_check_hyperv_vm_nic(item: str, expected_state: State, expected_summary: str) -> None:
    result = list(check_hyperv_vm_nic(item, test_section))
    assert len(result) == 1
    if isinstance(result[0], Result):
        assert result[0].state == expected_state
        assert result[0].summary == expected_summary
