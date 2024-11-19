#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


import time
from collections.abc import Mapping, MutableMapping, Sequence
from typing import Any, TypedDict

from cmk.agent_based.v2 import (
    CheckPlugin,
    CheckResult,
    DiscoveryResult,
    get_rate,
    get_value_store,
    GetRateError,
    IgnoreResults,
    Result,
    Service,
    SNMPSection,
    SNMPTree,
    State,
    StringTable,
)
from cmk.plugins.lib.diskstat import check_diskstat_dict_legacy
from cmk.plugins.lib.ucd_hr_detection import UCD


class Disk(TypedDict):
    disk_index: str
    read_throughput: float
    write_throughput: float
    read_ios: float
    write_ios: float


Section = Mapping[str, Disk]


def parse_ucd_diskio(string_table: Sequence[StringTable]) -> Section:
    section: dict[str, Disk] = {}

    if not string_table:
        return section

    for line in string_table[0]:
        if len(line) != 6:
            continue

        disk_index, name, read_size, write_size, read, write = line
        try:
            section[name] = {
                "disk_index": disk_index,
                "read_throughput": float(read_size),
                "write_throughput": float(write_size),
                "read_ios": float(read),
                "write_ios": float(write),
            }
        except ValueError:
            pass

    return section


snmp_section_ucd_diskio = SNMPSection(
    name="ucd_diskio",
    parse_function=parse_ucd_diskio,
    fetch=[
        SNMPTree(
            base=".1.3.6.1.4.1.2021.13.15.1.1",
            oids=[
                "1",  # diskIOIndex
                "2",  # diskIODevice
                "3",  # diskIONRead
                "4",  # diskIONWritten
                "5",  # diskIOReads
                "6",  # diskIOWrites
            ],
        )
    ],
    detect=UCD,
)


def discover_ucd_diskio(section: Section) -> DiscoveryResult:
    yield from (Service(item=disk) for disk in section)


def check_ucd_diskio(
    item: str,
    params: Mapping[str, Any],
    section: Section,
) -> CheckResult:
    yield from _check_ucd_diskio(
        item=item,
        params=params,
        section=section,
        this_time=time.time(),
        value_store=get_value_store(),
    )


def _check_ucd_diskio(
    item: str,
    params: Mapping[str, Any],
    section: Section,
    value_store: MutableMapping,
    this_time: float,
) -> CheckResult:
    if (disk := section.get(item)) is None:
        return

    disk_data: dict[str, float] = {}

    for key in ["read_ios", "write_ios", "read_throughput", "write_throughput"]:
        if (value := disk.get(key)) is None:
            continue

        if isinstance(value, float):
            try:
                disk_data[key] = get_rate(
                    value_store, f"ucd_disk_io_{key}.{item}", this_time, value
                )
            except GetRateError:
                yield IgnoreResults()

    yield Result(state=State.OK, summary=f"[{disk['disk_index']}]")

    yield from check_diskstat_dict_legacy(
        params=params,
        disk=disk_data,
        value_store=value_store,
        this_time=time.time(),
    )


check_plugin_ucd_diskio = CheckPlugin(
    name="ucd_diskio",
    service_name="Disk IO %s",
    discovery_function=discover_ucd_diskio,
    check_function=check_ucd_diskio,
    check_ruleset_name="diskstat",
    check_default_parameters={},
)
