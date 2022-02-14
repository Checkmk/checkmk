#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2021 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections import defaultdict
from dataclasses import dataclass, field
from itertools import chain
from typing import Dict

from .agent_based_api.v1 import register
from .agent_based_api.v1.type_defs import StringTable
from .utils import diskstat, docker
from .utils.docker import is_string_table_heading

MAPPING = {
    ("io_service_bytes_recursive", "read"): "read_throughput",
    ("io_service_bytes_recursive", "write"): "write_throughput",
    ("io_serviced_recursive", "read"): "read_ios",
    ("io_serviced_recursive", "write"): "write_ios",
}


def __parse_docker_api(data, docker_key_name):
    for entry in data[docker_key_name] or ():
        yield f'{entry["major"]}:{entry["minor"]}', docker_key_name, entry["op"], entry["value"]


def _parse_docker_container_diskstat_plugin(info: StringTable) -> diskstat.Section:
    raw = docker.parse(info).data

    devices_by_name: Dict[str, Dict[str, float]] = {}
    devices_by_number: Dict[str, Dict[str, float]] = {}
    for major_minor, name in raw["names"].items():
        devices_by_name[name] = devices_by_number[major_minor] = {
            "timestamp": raw["time"],
        }

    for major_minor, docker_key_name, docker_op, value in chain(
        __parse_docker_api(raw, "io_service_bytes_recursive"),
        __parse_docker_api(raw, "io_serviced_recursive"),
    ):
        diskstat_key = MAPPING.get((docker_key_name, docker_op.lower()))
        if diskstat_key is not None:
            devices_by_number[major_minor][diskstat_key] = value

    return devices_by_name


@dataclass
class ParsedDiskstatData:
    time: int = 0
    names: Dict[str, str] = field(default_factory=dict)
    # names[device_number] = device_name
    stat: Dict[str, Dict[str, Dict[str, int]]] = field(
        default_factory=lambda: defaultdict(lambda: defaultdict(dict))
    )
    # stat[device_number][headline][counter_name] = value


def _parse_docker_container_diskstat_agent(info: StringTable) -> diskstat.Section:
    lines_by_headline = defaultdict(list)
    current_headline = None
    for line in info:
        if is_string_table_heading(line):
            current_headline = line[0]
            continue
        lines_by_headline[current_headline].append(line)

    parsed = ParsedDiskstatData()
    parsed.time = int(lines_by_headline["[time]"][0][0])
    for headline in ("[io_service_bytes]", "[io_serviced]"):
        for line in lines_by_headline[headline]:
            if len(line) == 2 and line[0] == "Total":
                continue
            parsed.stat[line[0]][headline][line[1]] = int(line[2])
    for line in lines_by_headline["[names]"]:
        parsed.names[line[1]] = line[0]

    section: Dict[str, Dict[str, float]] = {}
    for device_number, stats in parsed.stat.items():
        device_name = parsed.names[device_number]
        section[device_name] = {
            "timestamp": parsed.time,
            "read_ios": stats["[io_serviced]"]["Read"],
            "write_ios": stats["[io_serviced]"]["Write"],
            "read_throughput": stats["[io_service_bytes]"]["Read"],
            "write_throughput": stats["[io_service_bytes]"]["Write"],
        }

    return section


def parse_docker_container_diskstat(string_table: StringTable) -> diskstat.Section:
    version = docker.get_version(string_table)
    if version is None:
        result = _parse_docker_container_diskstat_agent(string_table)
    else:
        result = _parse_docker_container_diskstat_plugin(string_table)

    filtered_result = {}
    for device_name, data in result.items():
        if device_name.startswith("loop"):
            continue
        if sum(i[1] for i in data.items() if i[0] != "timestamp") == 0:
            # all counters are 0
            continue
        filtered_result[device_name] = data

    return filtered_result


register.agent_section(
    name="docker_container_diskstat",
    parse_function=parse_docker_container_diskstat,
    parsed_section_name="diskstat",
)
