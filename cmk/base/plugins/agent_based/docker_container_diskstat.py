#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2021 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from typing import Dict, Iterable, Iterator, Literal, Tuple, TypedDict

from .agent_based_api.v1 import register
from .agent_based_api.v1.type_defs import StringTable
from .utils import diskstat, docker


class DeviceData(TypedDict):
    name: str
    bytes: Dict[str, int]
    ios: Dict[str, int]


Devices = Dict[Tuple[int, int], DeviceData]


class PreParsed(TypedDict):
    time: int
    devices: Devices


Section = Dict[str, Tuple[int, DeviceData]]


def _parse_docker_container_diskstat_plugin(info: StringTable) -> PreParsed:
    raw = docker.json_get_obj(info[1])

    devices: Devices = {}
    for major_minor, name in raw["names"].items():
        major, minor = map(int, major_minor.split(":", 1))
        devices[(major, minor)] = {
            "name": name,
            "bytes": {},
            "ios": {},
        }

    for entry in raw["io_service_bytes_recursive"] or ():
        device = devices.get((entry["major"], entry["minor"]))
        if device:
            device["bytes"][entry["op"].title()] = entry["value"]

    for entry in raw["io_serviced_recursive"] or ():
        device = devices.get((entry["major"], entry["minor"]))
        if device:
            device["ios"][entry["op"].title()] = entry["value"]

    # only keep devices with counters
    devices_with_counters = {}
    for major_minor, diskstat_data in devices.items():
        if diskstat_data["bytes"] or diskstat_data["ios"]:
            devices_with_counters[major_minor] = diskstat_data

    return {"time": raw["time"], "devices": devices_with_counters}


def _parse_docker_container_diskstat_agent(info: StringTable) -> PreParsed:
    sections: PreParsed = {}  # type: ignore[typeddict-item]

    phase: Literal["bytes", "ios", "names", "time"]
    for line in info:

        if line[0] == "[io_service_bytes]":
            phase = "bytes"
        elif line[0] == "[io_serviced]":
            phase = "ios"
        elif line[0] == "[names]":
            phase = "names"
        elif line[0] == "[time]":
            phase = "time"
        else:
            if line[0] == "Total":
                continue

            if phase == "time":
                sections["time"] = int(line[0])
                continue

            devices = sections.setdefault("devices", {})

            if phase == "names":
                major, minor = map(int, line[1].split(":"))
            else:
                major, minor = map(int, line[0].split(":"))

            device_id = major, minor
            device = devices.setdefault(device_id, {})  # type: ignore[typeddict-item]

            if phase == "names":
                device["name"] = line[0]
            else:
                device_phase = device.setdefault(phase, {})  # type: ignore[arg-type]
                device_phase[line[1]] = int(line[2])

    return sections


MAPPING: Iterable[Tuple[str, Literal["ios", "bytes"], str]] = [
    ("read_ios", "ios", "Read"),
    ("write_ios", "ios", "Write"),
    ("read_throughput", "bytes", "Read"),
    ("write_throughput", "bytes", "Write"),
]


def parse_docker_container_diskstat(string_table: StringTable) -> diskstat.Section:

    version = docker.get_version(string_table)
    if version is None:
        pre_parsed = _parse_docker_container_diskstat_agent(string_table)
    else:
        pre_parsed = _parse_docker_container_diskstat_plugin(string_table)

    def _filter(devices: Iterable[DeviceData]) -> Iterator[DeviceData]:
        # Filter out unwanted things
        for device in devices:
            if device["name"].startswith("loop"):
                continue

            # Skip devices without counts
            if "ios" not in device or "bytes" not in device:
                continue
            yield device

    section: Dict[str, Dict[str, float]] = {}
    this_time = pre_parsed["time"]

    for pre_parsed_device in _filter(pre_parsed["devices"].values()):
        device: Dict[str, float] = {}
        section[pre_parsed_device["name"]] = device
        old_key_1: Literal["ios", "bytes"]
        for new_key, old_key_1, old_key_2 in MAPPING:
            if old_key_1 in pre_parsed_device and old_key_2 in pre_parsed_device[old_key_1]:
                device[new_key] = pre_parsed_device[old_key_1][old_key_2]
        device["timestamp"] = this_time

    return section


register.agent_section(
    name="docker_container_diskstat",
    parse_function=parse_docker_container_diskstat,
    parsed_section_name="diskstat",
)
