#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.agent_based.v2 import Result, Service, State
from cmk.plugins.vsphere.agent_based.esx_vsphere_vm import parse_esx_vsphere_vm
from cmk.plugins.vsphere.agent_based.esx_vsphere_vm_mounted_devices import (
    check_esx_vsphere_vm_mounted_devices,
    discover_esx_vsphere_vm_mounted_devices,
)
from cmk.plugins.vsphere.lib.esx_vsphere import SectionESXVm


def _device(device_type: str, label: str, *, connected: bool) -> str:
    return (
        f"virtualDeviceType {device_type}|label {label}|summary {label}|startConnected false"
        f"|allowGuestControl true|connected {'true' if connected else 'false'}|status ok"
    )


def _section_with(*devices: str) -> SectionESXVm:
    agent_line = ["config.hardware.device", *"@@".join(devices).split(" ")]
    section = parse_esx_vsphere_vm([agent_line])
    assert section is not None
    return section


def test_vm_with_device_information_is_discovered() -> None:
    section = _section_with(_device("VirtualCdrom", "CD/DVD drive 1", connected=False))

    assert list(discover_esx_vsphere_vm_mounted_devices(section)) == [Service()]


def test_vm_without_device_information_is_not_discovered() -> None:
    section = parse_esx_vsphere_vm([["name", "web-01"]])
    assert section is not None

    assert list(discover_esx_vsphere_vm_mounted_devices(section)) == []


def test_connected_cdrom_endangers_high_availability() -> None:
    section = _section_with(_device("VirtualCdrom", "CD/DVD drive 1", connected=True))

    assert list(check_esx_vsphere_vm_mounted_devices(section)) == [
        Result(
            state=State.WARN,
            summary="HA functionality not guaranteed, Mounted devices: CD/DVD drive 1",
        )
    ]


def test_all_connected_removable_devices_are_listed() -> None:
    section = _section_with(
        _device("VirtualCdrom", "CD/DVD drive 1", connected=True),
        _device("VirtualFloppy", "Floppy drive 1", connected=True),
    )

    (result,) = check_esx_vsphere_vm_mounted_devices(section)

    assert isinstance(result, Result)
    assert result.summary.endswith("Mounted devices: CD/DVD drive 1, Floppy drive 1")


def test_disconnected_removable_devices_keep_high_availability() -> None:
    section = _section_with(
        _device("VirtualCdrom", "CD/DVD drive 1", connected=False),
        _device("VirtualFloppy", "Floppy drive 1", connected=False),
    )

    assert list(check_esx_vsphere_vm_mounted_devices(section)) == [
        Result(state=State.OK, summary="HA functionality guaranteed")
    ]


def test_connected_non_removable_devices_are_ignored() -> None:
    section = _section_with(_device("VirtualE1000", "Network adapter 1", connected=True))

    assert list(check_esx_vsphere_vm_mounted_devices(section)) == [
        Result(state=State.OK, summary="HA functionality guaranteed")
    ]
