#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2021 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
from .agent_based_api.v1 import register
from .agent_based_api.v1.type_defs import StringTable
from .utils import docker, memory


def parse_docker_container_mem_cgroupv2(string_table: StringTable) -> memory.SectionMemUsed:
    parsed = docker.parse_container_memory(string_table, cgroup=2)
    return parsed.to_mem_used()


register.agent_section(
    name="docker_container_mem_cgroupv2",
    parse_function=parse_docker_container_mem_cgroupv2,
    parsed_section_name="mem_used",
)
