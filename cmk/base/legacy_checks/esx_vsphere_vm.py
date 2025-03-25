#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# .
#   .--VM devices----------------------------------------------------------.
#   |         __     ____  __       _            _                         |
#   |         \ \   / /  \/  |   __| | _____   _(_) ___ ___  ___           |
#   |          \ \ / /| |\/| |  / _` |/ _ \ \ / / |/ __/ _ \/ __|          |
#   |           \ V / | |  | | | (_| |  __/\ V /| | (_|  __/\__ \          |
#   |            \_/  |_|  |_|  \__,_|\___| \_/ |_|\___\___||___/          |
#   |                                                                      |
#   '----------------------------------------------------------------------'


from cmk.agent_based.legacy.v0_unstable import LegacyCheckDefinition

check_info = {}


def parse_esx_vsphere_vm_mounted_devices(section):
    data = section.mounted_devices
    parsed: dict[str, dict[str, str]] = {}
    for device_data in " ".join(data).split("@@"):
        if "|" not in device_data:
            continue
        device_attrs: dict[str, str] = {}
        for entry in device_data.split("|"):
            k, v = entry.split(" ", 1)
            device_attrs.setdefault(k, v)
        device_name = device_attrs["label"]
        del device_attrs["label"]
        parsed.setdefault(device_name, device_attrs)
    return parsed


def inventory_esx_vsphere_vm_mounted_devices(section):
    if parse_esx_vsphere_vm_mounted_devices(section):
        return [(None, None)]
    return []


def check_esx_vsphere_vm_mounted_devices(item, params, section):
    device_types = ["VirtualCdrom", "VirtualFloppy"]
    mounted_devices = []
    for device_name, attrs in parse_esx_vsphere_vm_mounted_devices(section).items():
        if attrs["virtualDeviceType"] in device_types and attrs["connected"] == "true":
            mounted_devices.append(device_name)

    if mounted_devices:
        return 1, "HA functionality not guaranteed, Mounted devices: %s" % ", ".join(
            mounted_devices
        )
    return 0, "HA functionality guaranteed"


check_info["esx_vsphere_vm.mounted_devices"] = LegacyCheckDefinition(
    name="esx_vsphere_vm_mounted_devices",
    service_name="ESX Mounted Devices",
    sections=["esx_vsphere_vm"],
    discovery_function=inventory_esx_vsphere_vm_mounted_devices,
    check_function=check_esx_vsphere_vm_mounted_devices,
)
