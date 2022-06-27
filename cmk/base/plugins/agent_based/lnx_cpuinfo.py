#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


import re
from typing import Mapping, Union

from .agent_based_api.v1 import Attributes, register
from .agent_based_api.v1.type_defs import InventoryResult, StringTable

Section = Mapping[str, Union[str, int]]


def parse_lnx_cpuinfo(string_table: StringTable) -> Section:
    """
    The parse / inventorize separation in this plugin is a result of a brainless migration --
    feel free to improve it.
    """
    node: dict[str, Union[str, int]] = {}
    num_threads_total = 0
    sockets = set([])
    for varname, value in string_table:
        if varname == "cpu cores":
            node["cores_per_cpu"] = int(value)
        elif varname == "siblings":
            node["threads_per_cpu"] = int(value)
        elif varname == "vendor_id":
            node["vendor"] = {
                "GenuineIntel": "intel",
                "AuthenticAMD": "amd",
            }.get(value, value)
        elif varname == "cache size":
            node["cache_size"] = int(value.split()[0]) * 1024  # everything is normalized to bytes!
        elif varname == "model name":
            node["model"] = value
        # For the following two entries we assume that all
        # entries are numbered in increasing order in /proc/cpuinfo.
        elif varname == "processor":
            num_threads_total = int(value) + 1
        elif varname == "physical id":
            sockets.add(int(value))
        elif varname == "flags":
            if re.search(" lm ", value):
                node["arch"] = "x86_64"
            else:
                node["arch"] = "i386"

    num_sockets = len(sockets)

    if num_threads_total:
        node.setdefault("cores_per_cpu", 1)
        node.setdefault("threads_per_cpu", 1)
        node["cores"] = num_sockets * node["cores_per_cpu"]
        node["threads"] = num_sockets * node["threads_per_cpu"]
        node["cpus"] = num_sockets

    return node


register.agent_section(
    name="lnx_cpuinfo",
    parse_function=parse_lnx_cpuinfo,
)


# Note: This node is also being filled by dmidecode
def inventory_lnx_cpuinfo(section: Section) -> InventoryResult:
    yield Attributes(
        path=["hardware", "cpu"],
        inventory_attributes=section,
    )


register.inventory_plugin(
    name="lnx_cpuinfo",
    inventory_function=inventory_lnx_cpuinfo,
)
