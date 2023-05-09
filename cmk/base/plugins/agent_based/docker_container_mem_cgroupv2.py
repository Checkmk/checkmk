#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2021 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
from typing import Dict, List
from .agent_based_api.v1.type_defs import StringTable

from .agent_based_api.v1 import register


def _mem_bytes(line: List[str]) -> int:
    if len(line) == 2 and line[1] == 'kB':
        return int(line[0]) * 1024
    return int(line[0])


def parse_docker_container_mem_cgroupv2(string_table: StringTable) -> Dict[str, int]:

    parsed = {line[0]: line[1:] for line in string_table}
    host_memory_total = _mem_bytes(parsed["MemTotal:"])

    container_memory_usage = _mem_bytes(parsed["memory.current"])
    if (memory_max := parsed["memory.max"]) == ['max']:
        container_memory_total = host_memory_total
    else:
        container_memory_total = _mem_bytes(memory_max)
    container_memory_total_inactive_file = _mem_bytes(parsed["inactive_file"])

    return {
        "MemTotal": container_memory_total,
        "MemFree": container_memory_total -
                   max(container_memory_usage - container_memory_total_inactive_file, 0),
    }


register.agent_section(
    name="docker_container_mem_cgroupv2",
    parse_function=parse_docker_container_mem_cgroupv2,
    parsed_section_name="mem_used",
)
