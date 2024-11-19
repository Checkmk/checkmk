#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
import json
import time
from collections.abc import Mapping, MutableMapping
from typing import Any

from cmk.agent_based.v2 import (
    AgentSection,
    CheckPlugin,
    CheckResult,
    DiscoveryResult,
    get_value_store,
    Service,
    StringTable,
)
from cmk.plugins.lib.diskstat import check_diskstat_dict_legacy

Section = Mapping[str, MutableMapping[str, float]]


def parse_cadvisor_diskstat(string_table: StringTable) -> Section:
    diskstat_mapping = {
        "disk_utilisation": "utilization",
        "disk_write_operation": "write_ios",
        "disk_read_operation": "read_ios",
        "disk_write_throughput": "write_throughput",
        "disk_read_throughput": "read_throughput",
    }

    section: dict[str, float] = {}
    for diskstat_name, diskstat_entries in json.loads(string_table[0][0]).items():
        if len(diskstat_entries) != 1:
            continue
        try:
            section[diskstat_mapping[diskstat_name]] = float(diskstat_entries[0]["value"])
        except KeyError:
            continue

    return {"Summary": section}


agent_section_cadvisor_diskstat = AgentSection(
    name="cadvisor_diskstat",
    parse_function=parse_cadvisor_diskstat,
)


def discover_cadvisor_diskstat(section: Section) -> DiscoveryResult:
    for disk in section:
        yield Service(item=disk)


def check_cadvisor_diskstat(item: str, params: Mapping[str, Any], section: Section) -> CheckResult:
    if (disk := section.get(item)) is None:
        return

    yield from check_diskstat_dict_legacy(
        params=params,
        disk=disk,
        value_store=get_value_store(),
        this_time=time.time(),
    )


check_plugin_cadvisor_diskstat = CheckPlugin(
    name="cadvisor_diskstat",
    service_name="Disk IO %s",
    discovery_function=discover_cadvisor_diskstat,
    check_function=check_cadvisor_diskstat,
    check_ruleset_name="diskstat",
    check_default_parameters={},
)
