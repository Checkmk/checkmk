#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2021 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from typing import Optional

from .agent_based_api.v1 import register
from .agent_based_api.v1.type_defs import StringTable
from .utils import docker
from .utils.cpu_utilization_os import SectionCpuUtilizationOs


def __parse_docker_container_cpu(info):
    parsed = {}
    version = docker.get_version(info)
    if version is None:
        # agent running inside a docker container
        for line in info:
            if line[0] == "cpu":
                parsed["system_ticks"] = sum(map(int, line[1:]))
            else:
                parsed[line[0]] = int(line[1])
        if "user" in parsed and "system" in parsed:
            parsed["container_ticks"] = parsed["user"] + parsed["system"]
        return parsed

    # data comes from mk_docker.py agent plugin
    raw = docker.parse(info).data
    # https://github.com/moby/moby/blob/646072ed6524f159c214f830f0049369db5a9441/docs/api/v1.41.yaml#L6125-L6127
    if (online_cpus := raw.get("online_cpus")) is not None:
        num_cpus = online_cpus
    elif (percpu_usage_len := len(raw["cpu_usage"].get("percpu_usage", []))) != 0:
        num_cpus = percpu_usage_len
    else:
        return {}
    parsed["num_cpus"] = num_cpus
    parsed["system_ticks"] = raw["system_cpu_usage"]
    parsed["container_ticks"] = raw["cpu_usage"]["total_usage"]
    return parsed


def parse_docker_container_cpu_cgroupv1(
    string_table: StringTable,
) -> Optional[SectionCpuUtilizationOs]:
    result = __parse_docker_container_cpu(string_table)
    if not result:
        return None
    return SectionCpuUtilizationOs(
        # system_ticks ticks 4 times for 4 cores per time interval
        time_base=result["system_ticks"] / result["num_cpus"],
        time_cpu=result["container_ticks"],
        num_cpus=result["num_cpus"],
    )


register.agent_section(
    name="docker_container_cpu",
    parsed_section_name="cpu_utilization_os",
    parse_function=parse_docker_container_cpu_cgroupv1,
)
