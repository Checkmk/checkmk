#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from dataclasses import asdict, dataclass

from .agent_based_api.v1 import Attributes, register
from .agent_based_api.v1.type_defs import InventoryResult, StringTable


@dataclass
class _Section:
    cores_per_cpu: int = 1
    threads_per_cpu: int = 1
    vendor: str | None = None
    cache_size: int | None = None
    model: str | None = None
    cpus: int | None = None
    voltage: float | None = None
    max_speed: float | None = None
    arch: str | None = None
    cores: int | None = None
    threads: int | None = None


def _parse_speed(v: str) -> float | None:  # into Hz (float)
    if not v or v == "Unknown":
        return None

    match v.split()[:2]:
        case [value, "GHz"]:
            return float(value) * 1000.0**3
        case [value] | [value, "MHz"]:
            return float(value) * 1000.0**2
        case [value, "kHz"]:
            return float(value) * 1000.0
        case [value, "Hz"]:
            return float(value)

    return None


def _parse_voltage(v: str) -> float | None:
    if not v or v == "Unknown":
        return None
    return float(v.split()[0])


def parse_win_cpuinfo(string_table: StringTable) -> _Section:

    section = _Section()

    for key, value in ((k.strip(), v.strip()) for k, v in string_table):

        match key:
            case "NumberOfCores":
                if value:
                    section.cores_per_cpu = int(value)
            case "NumberOfLogicalProcessors":
                if value:
                    section.threads_per_cpu = int(value)
            case "Manufacturer":
                section.vendor = {"GenuineIntel": "intel", "AuthenticAMD": "amd"}.get(value, value)
            case "L2CacheSize":
                # There is also the L3CacheSize
                if value:
                    section.cache_size = int(value) * 1024
            case "Name":
                section.model = value
            # For the following two entries we assume that all
            # entries are numbered in increasing order in /proc/cpuinfo.
            case "DeviceID":
                section.cpus = (section.cpus or 0) + 1
            case "CurrentVoltage":
                section.voltage = _parse_voltage(value)
            case "MaxClockSpeed":
                section.max_speed = _parse_speed(value)
            case "Architecture":
                section.arch = {
                    "0": "i386",
                    "1": "MIPS",
                    "2": "Alpha",
                    "3": "PowerPC",
                    "6": "Itanium",
                    "9": "x86_64",
                }.get(value, value)

    if section.cpus:
        section.cores = section.cores_per_cpu * section.cpus
        section.threads = section.threads_per_cpu * section.cpus

    return section


def inventory_win_cpuinfo(section: _Section) -> InventoryResult:
    yield Attributes(
        path=["hardware", "cpu"],
        inventory_attributes={k: v for k, v in asdict(section).items() if v is not None},
    )


register.inventory_plugin(
    name="win_cpuinfo",
    inventory_function=inventory_win_cpuinfo,
)
