#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from typing import Any, Mapping, Optional

from .agent_based_api.v1 import get_value_store, register, Service, SNMPTree
from .agent_based_api.v1.type_defs import CheckResult, DiscoveryResult, StringTable
from .utils.df import df_check_filesystem_single, FILESYSTEM_DEFAULT_LEVELS
from .utils.fortinet import DETECT_FORTISANDBOX

Section = Mapping[str, int]


def parse_fortisandbox_disk(string_table: StringTable) -> Optional[Section]:
    """
    >>> parse_fortisandbox_disk([["1000", "2000"]])
    {'used': 1000, 'cap': 2000}
    """
    return (
        {
            "used": int(string_table[0][0]),
            "cap": int(string_table[0][1]),
        }
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
        size_mb=section["cap"],
        avail_mb=section["cap"] - section["disk_used"],
        reserved_mb=0,
        inodes_total=None,
        inodes_avail=None,
        params=params,
    )


register.snmp_section(
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

register.check_plugin(
    name="fortisandbox_disk_usage",
    service_name="Disk usage %s",
    discovery_function=discover_fortisandbox_disk,
    check_function=check_fortisandbox_disk,
    check_default_parameters=FILESYSTEM_DEFAULT_LEVELS,
    check_ruleset_name="filesystem",
)
