#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
from .agent_based_api.v1 import HostLabel, register
from .agent_based_api.v1.type_defs import StringTable
from .utils.esx_vsphere import SectionVM


def parse_esx_vsphere_vm(string_table: StringTable) -> SectionVM:
    section: SectionVM = {}
    for line in string_table:
        # Do not monitor VM templates
        if line[0] == "config.template" and line[1] == "true":
            return {}
        section[line[0]] = line[1:]
    return section


def host_label_esx_vshpere_vm(section):
    if "runtime.host" in section:
        yield HostLabel("cmk/vsphere_object", "vm")


register.agent_section(
    name="esx_vsphere_vm",
    parse_function=parse_esx_vsphere_vm,
    host_label_function=host_label_esx_vshpere_vm,
)
