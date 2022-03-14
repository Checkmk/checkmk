#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2021 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from typing import Optional

from .agent_based_api.v1 import register
from .agent_based_api.v1.type_defs import StringTable
from .utils.cpu_utilization_os import SectionCpuUtilizationOs


def parse_docker_container_cpu_cgroupv1(
    string_table: StringTable,
) -> Optional[SectionCpuUtilizationOs]:

    parsed = {}
    for line in string_table:
        key = line[0]
        if key == "cpu":
            parsed["system_ticks"] = sum(map(int, line[1:]))
            continue
        value = int(line[1])
        parsed[key] = value

    if not set(parsed.keys()).issuperset(set(["user", "system", "system_ticks", "num_cpus"])):
        return None

    return SectionCpuUtilizationOs(
        # system_ticks ticks 4 times for 4 cores per time interval
        time_base=parsed["system_ticks"] / parsed["num_cpus"],
        time_cpu=parsed["user"] + parsed["system"],
        num_cpus=parsed["num_cpus"],
    )


register.agent_section(
    name="lxc_container_cpu",
    parsed_section_name="cpu_utilization_os",
    parse_function=parse_docker_container_cpu_cgroupv1,
)
