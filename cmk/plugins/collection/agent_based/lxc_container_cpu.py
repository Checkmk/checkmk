#!/usr/bin/env python3
# Copyright (C) 2021 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


from cmk.agent_based.v2 import AgentSection, StringTable
from cmk.plugins.lib.cpu_utilization_os import SectionCpuUtilizationOs


def parse_docker_container_cpu_cgroupv1(
    string_table: StringTable,
) -> SectionCpuUtilizationOs | None:
    parsed = {}
    for line in string_table:
        key = line[0]
        if key == "cpu":
            parsed["system_ticks"] = sum(map(int, line[1:]))
            continue
        value = int(line[1])
        parsed[key] = value

    if not set(parsed.keys()).issuperset({"user", "system", "system_ticks", "num_cpus"}):
        return None

    return SectionCpuUtilizationOs(
        # system_ticks ticks 4 times for 4 cores per time interval
        time_base=parsed["system_ticks"] / parsed["num_cpus"],
        time_cpu=parsed["user"] + parsed["system"],
        num_cpus=parsed["num_cpus"],
    )


agent_section_lxc_container_cpu = AgentSection(
    name="lxc_container_cpu",
    parsed_section_name="cpu_utilization_os",
    parse_function=parse_docker_container_cpu_cgroupv1,
)
