#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
import json
import time
from collections.abc import Mapping, MutableMapping
from typing import Any

from cmk.base.plugins.agent_based.agent_based_api.v1.type_defs import (
    CheckResult,
    DiscoveryResult,
    StringTable,
)
from cmk.base.plugins.agent_based.utils.diskstat import check_diskstat_dict

from .agent_based_api.v1 import get_value_store, register, Service

Section = Mapping[str, MutableMapping[str, float]]


def parse_cadvisor_diskstat(string_table: StringTable) -> Section:
    diskstat_mapping = {
        "disk_utilisation": "utilization",
        "disk_write_operation": "write_ios",
        "disk_read_operation": "read_ios",
        "disk_write_throughput": "write_throughput",
        "disk_read_throughput": "read_throughput",
    }

    section: MutableMapping[str, float] = {}
    for diskstat_name, diskstat_entries in json.loads(string_table[0][0]).items():
        if len(diskstat_entries) != 1:
            continue
        try:
            section[diskstat_mapping[diskstat_name]] = float(diskstat_entries[0]["value"])
        except KeyError:
            continue

    return {"Summary": section}


register.agent_section(
    name="cadvisor_diskstat",
    parse_function=parse_cadvisor_diskstat,
)


def discover_cadvisor_diskstat(section: Section) -> DiscoveryResult:
    for disk in section:
        yield Service(item=disk)


def check_cadvisor_diskstat(item: str, params: Mapping[str, Any], section: Section) -> CheckResult:

    if (disk := section.get(item)) is None:
        return

    yield from check_diskstat_dict(
        params=params,
        disk=disk,
        value_store=get_value_store(),
        this_time=time.time(),
    )


register.check_plugin(
    name="cadvisor_diskstat",
    service_name="Disk IO %s",
    discovery_function=discover_cadvisor_diskstat,
    check_function=check_cadvisor_diskstat,
    check_ruleset_name="diskstat",
    check_default_parameters={},
)
