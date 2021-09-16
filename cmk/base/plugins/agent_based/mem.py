#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from typing import Optional

from .agent_based_api.v1 import Attributes, register, type_defs
from .utils import memory


def parse_proc_meminfo_bytes(string_table: type_defs.StringTable) -> Optional[memory.SectionMem]:
    """Parse /proc/meminfo into the canonical form: into bytes

    >>> import pprint
    >>> section = parse_proc_meminfo_bytes([
    ...     ['MemTotal:', '377176', 'kB'],
    ...     ['MemFree:', '60112', 'kB'],
    ...     ['Buffers:', '93864', 'kB'],
    ...     ['Cached:', '116364', 'kB'],
    ...     ['SwapCached:', '0', 'kB'],
    ... ])
    >>> pprint.pprint(section)
    {'Buffers': 96116736,
     'Cached': 119156736,
     'MemFree': 61554688,
     'MemTotal': 386228224,
     'SwapCached': 0}

    """

    section = {}
    for line in string_table:
        value = int(line[1])
        if len(line) > 2 and line[2] == "kB":
            value *= 1024
        section[line[0][:-1]] = value
    return section or None


register.agent_section(
    name="mem",
    supersedes=["hr_mem"],
    parse_function=parse_proc_meminfo_bytes,
)


def inventory_mem(section: memory.SectionMem):
    yield Attributes(
        path=["hardware", "memory"],
        inventory_attributes={
            key_inventory: section[key_section]
            for key_inventory, key_section in [
                ("total_ram_usable", "MemTotal"),
                ("total_swap", "SwapTotal"),
                ("total_vmalloc", "VmallocTotal"),
            ]
            if key_section in section
        },
    )


register.inventory_plugin(
    name="mem",
    inventory_function=inventory_mem,
)
