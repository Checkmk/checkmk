#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Mapping

from cmk.agent_based.v2 import (
    AgentSection,
    Attributes,
    HostLabel,
    HostLabelGenerator,
    InventoryPlugin,
    InventoryResult,
    StringTable,
)

Section = Mapping[str, str]


def parse_esx_vsphere_systeminfo(string_table: StringTable) -> Section:
    """Load key/value pairs into dict

    Example:

        <<<esx_systeminfo>>>
        vendor VMware, Inc.
        name VMware ESXi
        propertyCollector ha-property-collector
        apiVersion 5.0
        sessionManager ha-sessionmgr
        osType vmnix-x86
        version 5.0.0
        build 914586
        licenseManager ha-license-manager
        perfManager ha-perfmgr
        rootFolder ha-folder-root

    """
    parsed = {}
    for line in string_table:
        parsed[line[0]] = " ".join(line[1:])
    return parsed


def host_label_esx_vshpere_systeminfo(section: Section) -> HostLabelGenerator:
    """Host label function

    Labels:

        cmk/vsphere_vcenter:
            This label is set to "yes" if the corresponding host is a VMware vCenter
            otherwise the label is not created.

        cmk/vsphere_object:
            This label is set to "server" if the host is an ESXi hostsystem
            and to "vm" if the host is a virtual machine.

    """
    name = section.get("name", "")
    if "vCenter" in name:
        yield HostLabel("cmk/vsphere_vcenter", "yes")
    if "ESXi" in name:
        yield HostLabel("cmk/vsphere_object", "server")


agent_section_esx_systeminfo = AgentSection(
    name="esx_systeminfo",
    parse_function=parse_esx_vsphere_systeminfo,
    host_label_function=host_label_esx_vshpere_systeminfo,
)


def inventory_esx_systeminfo(section: Section) -> InventoryResult:
    yield Attributes(
        path=["software", "os"],
        inventory_attributes={
            "arch": "x86_64",
            **{
                key: section[raw_key]
                for key, raw_key in (
                    ("vendor", "vendor"),
                    ("build", "build"),
                    ("name", "name"),
                    ("version", "version"),
                    ("type", "osType"),
                )
                if raw_key in section
            },
        },
    )


inventory_plugin_esx_systeminfo = InventoryPlugin(
    name="esx_systeminfo",
    inventory_function=inventory_esx_systeminfo,
)
