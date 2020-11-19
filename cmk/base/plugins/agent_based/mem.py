#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from typing import Dict, Optional
from .agent_based_api.v1 import (
    register,
    type_defs,
    Attributes,
)


def parse_proc_meminfo_bytes(string_table: type_defs.StringTable) -> Optional[Dict[str, int]]:
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
        if len(line) > 2 and line[2] == 'kB':
            value *= 1024
        section[line[0][:-1]] = value
    return section or None


register.agent_section(
    name="mem",
    supersedes=["hr_mem"],
    parse_function=parse_proc_meminfo_bytes,
)


def inventory_mem(section: Dict[str, int]):
    yield Attributes(
        path=["hardware", "memory"],
        inventory_attributes={
            "total_ram_usable": section["MemTotal"],
            "total_swap": section["SwapTotal"],
            "total_vmalloc": section["VmallocTotal"],
        },
    )


register.inventory_plugin(
    name='mem',
    inventory_function=inventory_mem,
)
