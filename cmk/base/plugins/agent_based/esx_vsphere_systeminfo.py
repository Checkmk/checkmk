#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from typing import Mapping

from .agent_based_api.v1 import Attributes, HostLabel, register
from .agent_based_api.v1.type_defs import HostLabelGenerator, InventoryResult, StringTable

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

        cmk/vsphere_object:
            This label is set to "vcenter" if the corresponding host is a
            VMWare vCenter, and to "server" if the host is an ESXi hostsystem.

    """
    name = section.get("name", "")
    if "vCenter" in name:
        yield HostLabel("cmk/vsphere_object", "vcenter")
    elif "ESXi" in name:
        yield HostLabel("cmk/vsphere_object", "server")


register.agent_section(
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
                    ("name", "name"),
                    ("version", "version"),
                    ("type", "osType"),
                )
                if raw_key in section
            },
        },
    )


register.inventory_plugin(
    name="esx_systeminfo",
    inventory_function=inventory_esx_systeminfo,
)
