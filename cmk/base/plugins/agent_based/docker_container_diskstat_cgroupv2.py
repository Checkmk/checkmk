#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2021 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from typing import Any, Mapping, Dict, Sequence, MutableMapping, NamedTuple, List
from contextlib import suppress
from dataclasses import dataclass, field

from .agent_based_api.v1.type_defs import StringTable, DiscoveryResult, CheckResult
from .agent_based_api.v1 import register, get_value_store
from .utils.df import FILESYSTEM_DEFAULT_LEVELS
from .utils import diskstat


class Device(NamedTuple):
    read_ios: int
    read_throughput: int
    write_ios: int
    write_throughput: int


class Section(Dict[str, Device], MutableMapping[str, Device]):  # pylint: disable=too-many-ancestors
    def __init__(self, time: int):
        super().__init__()
        self.time = time


@dataclass
class ParsedData:
    time: int = 0
    names: Dict[str, str] = field(default_factory=dict)
    stat: Dict[str, Dict[str, str]] = field(default_factory=dict)


def _to_diskstat_dict(section: Section) -> Dict[str, Dict[str, int]]:
    return {k: v._asdict() for k, v in section.items()}


def _is_a_heading(line: List[str]) -> bool:
    return len(line) == 1 and line[0].startswith("[") and line[0].endswith("]")


def discover_docker_container_diskstat_cgroupv2(
    params: Sequence[Mapping[str, Any]],
    section: Section,
) -> DiscoveryResult:
    # TODO: don't discover lvm volumes, see CMK-7333
    yield from diskstat.discovery_diskstat_generic(params, _to_diskstat_dict(section))


def parse_docker_container_diskstat_cgroupv2(string_table: StringTable) -> Section:
    parsed = ParsedData()
    lines = iter(string_table)
    for line in lines:
        with suppress(StopIteration):
            if line == ["[time]"]:
                parsed.time = int(next(lines)[0])
                continue
            if line == ["[io.stat]"]:
                while not _is_a_heading(line := next(lines)):
                    stat: Dict[str, str] = {}
                    for kv_pair in line[1:]:
                        key, value = kv_pair.split("=")
                        stat[key] = value
                    parsed.stat[line[0]] = stat
            if line == ["[names]"]:
                while not _is_a_heading(line := next(lines)):
                    parsed.names[line[1]] = line[0]

    section = Section(parsed.time)

    for device_number, stats in parsed.stat.items():
        device_name = parsed.names[device_number]
        section[device_name] = Device(
            read_ios=int(stats['rios']),
            write_ios=int(stats['wios']),
            read_throughput=int(stats['rbytes']),
            write_throughput=int(stats['wbytes']),
        )

    return section


def check_docker_container_diskstat_cgroupv2(
    item: str,
    params: Mapping[str, Any],
    section: Section,
) -> CheckResult:
    value_store = get_value_store()
    yield from _check_docker_container_diskstat_cgroupv2(item, params, section, value_store)


def _check_docker_container_diskstat_cgroupv2(
    item: str,
    params: Mapping[str, Any],
    section: Section,
    value_store: MutableMapping[str, Any],
) -> CheckResult:
    if item == 'SUMMARY':

        def _compute_rates_single_disk(
            disk_absolute: diskstat.Disk,
            value_store: MutableMapping[str, Any],
            value_store_suffix: str,
        ) -> diskstat.Disk:
            return diskstat.compute_rates(
                disk=disk_absolute,
                value_store=value_store,
                disk_name=value_store_suffix,
                this_time=section.time,
            )

        disks_absolute = _to_diskstat_dict(section)
        disks_rate = diskstat.compute_rates_multiple_disks(
            disks_absolute,
            value_store,
            _compute_rates_single_disk,
        )
        rate = diskstat.summarize_disks(iter(disks_rate.items()))
    else:
        disk_absolute = _to_diskstat_dict(section)[item]
        rate = diskstat.compute_rates(
            disk=disk_absolute,
            value_store=value_store,
            disk_name=f"diskstat_{item}_",
            this_time=section.time,
        )
    yield from diskstat.check_diskstat_dict(
        params=params,
        disk=rate,
        value_store=value_store,
        this_time=section.time,
    )


register.agent_section(
    name="docker_container_diskstat_cgroupv2",
    parse_function=parse_docker_container_diskstat_cgroupv2,
)

register.check_plugin(
    name="docker_container_diskstat_cgroupv2",
    service_name="Disk IO %s",
    discovery_function=discover_docker_container_diskstat_cgroupv2,
    discovery_default_parameters={'summary': True},
    discovery_ruleset_name="diskstat_inventory",
    discovery_ruleset_type=register.RuleSetType.ALL,
    check_function=check_docker_container_diskstat_cgroupv2,
    check_ruleset_name="diskstat",
    check_default_parameters=FILESYSTEM_DEFAULT_LEVELS,
)
