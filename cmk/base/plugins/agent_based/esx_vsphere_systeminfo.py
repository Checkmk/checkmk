#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
from .agent_based_api.v1 import register, HostLabel


def parse_esx_vsphere_systeminfo(string_table):
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


def host_label_esx_vshpere_systeminfo(section):
    name = section.get("name", "")
    if "vCenter" in name:
        yield HostLabel(u"cmk/vsphere_object", u"vcenter")
    elif "ESXi" in name:
        yield HostLabel(u"cmk/vsphere_object", u"server")


register.agent_section(
    name="esx_systeminfo",
    parse_function=parse_esx_vsphere_systeminfo,
    host_label_function=host_label_esx_vshpere_systeminfo,
)
