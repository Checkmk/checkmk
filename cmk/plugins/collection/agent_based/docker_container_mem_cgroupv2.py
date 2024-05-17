#!/usr/bin/env python3
# Copyright (C) 2021 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
from cmk.agent_based.v2 import AgentSection, StringTable
from cmk.plugins.lib import docker, memory


def parse_docker_container_mem_cgroupv2(string_table: StringTable) -> memory.SectionMemUsed | None:
    if (parsed := docker.parse_container_memory(string_table, cgroup=2)) is None:
        return None
    return parsed.to_mem_used()


agent_section_docker_container_mem_cgroupv2 = AgentSection(
    name="docker_container_mem_cgroupv2",
    parse_function=parse_docker_container_mem_cgroupv2,
    parsed_section_name="mem_used",
)
