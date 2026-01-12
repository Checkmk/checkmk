#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


import time
from collections.abc import Mapping
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
from cmk.plugins.emc.lib import DETECT_DATADOMAIN
from cmk.plugins.lib.df import (
    df_check_filesystem_list,
    EXCLUDED_MOUNTPOINTS,
    FILESYSTEM_DEFAULT_PARAMS,
)


def discover_emc_datadomain_fs(section: StringTable) -> DiscoveryResult:
    for line in section:
        if line[1] not in EXCLUDED_MOUNTPOINTS:
            yield Service(item=line[1])


def check_emc_datadomain_fs(
    item: str, params: Mapping[str, Any], section: StringTable
) -> CheckResult:
    fslist = []
    for line in section:
        if item == line[1] or "patterns" in params:
            size_mb = float(line[2]) * 1024.0
            avail_mb = float(line[4]) * 1024.0
            fslist.append((item, size_mb, avail_mb, 0))
    yield from df_check_filesystem_list(
        get_value_store(), item, params, fslist, this_time=time.time()
    )


def parse_emc_datadomain_fs(string_table: StringTable) -> StringTable:
    return string_table


snmp_section_emc_datadomain_fs = SimpleSNMPSection(
    name="emc_datadomain_fs",
    detect=DETECT_DATADOMAIN,
    fetch=SNMPTree(
        base=".1.3.6.1.4.1.19746.1.3.2.1.1",
        oids=["1", "3", "4", "5", "6", "7", "8"],
    ),
    parse_function=parse_emc_datadomain_fs,
)


check_plugin_emc_datadomain_fs = CheckPlugin(
    name="emc_datadomain_fs",
    service_name="DD-Filesystem %s",
    discovery_function=discover_emc_datadomain_fs,
    check_function=check_emc_datadomain_fs,
    check_ruleset_name="filesystem",
    check_default_parameters=FILESYSTEM_DEFAULT_PARAMS,
)
