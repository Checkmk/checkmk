#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any

from cmk.agent_based.v2 import (
    CheckPlugin,
    CheckResult,
    DiscoveryResult,
    get_value_store,
    Service,
    SimpleSNMPSection,
    SNMPTree,
    StringTable,
)
from cmk.plugins.lib.df import df_check_filesystem_single, FILESYSTEM_DEFAULT_PARAMS
from cmk.plugins.lib.fortinet import DETECT_FORTISANDBOX


@dataclass(frozen=True)
class Section:
    used: int
    cap: int


def parse_fortisandbox_disk(string_table: StringTable) -> Section | None:
    """
    >>> parse_fortisandbox_disk([["1000", "2000"]])
    Section(used=1000, cap=2000)
    """
    return (
        Section(
            used=int(string_table[0][0]),
            cap=int(string_table[0][1]),
        )
        if string_table
        else None
    )


def discover_fortisandbox_disk(section: Section) -> DiscoveryResult:
    yield Service(item="system")


def check_fortisandbox_disk(
    item: str,
    params: Mapping[str, Any],
    section: Section,
) -> CheckResult:
    yield from df_check_filesystem_single(
        value_store=get_value_store(),
        mountpoint=item,
        filesystem_size=section.cap,
        free_space=section.cap - section.used,
        reserved_space=0,
        inodes_total=None,
        inodes_avail=None,
        params=params,
    )


snmp_section_fortisandbox_disk_usage = SimpleSNMPSection(
    name="fortisandbox_disk_usage",
    parse_function=parse_fortisandbox_disk,
    detect=DETECT_FORTISANDBOX,
    fetch=SNMPTree(
        base=".1.3.6.1.4.1.12356.118.3.1",
        oids=[
            "5",  # fsaSysDiskUsage
            "6",  # fsaSysDiskCapacity
        ],
    ),
)

check_plugin_fortisandbox_disk_usage = CheckPlugin(
    name="fortisandbox_disk_usage",
    service_name="Disk usage %s",
    discovery_function=discover_fortisandbox_disk,
    check_function=check_fortisandbox_disk,
    check_default_parameters=FILESYSTEM_DEFAULT_PARAMS,
    check_ruleset_name="filesystem",
)
