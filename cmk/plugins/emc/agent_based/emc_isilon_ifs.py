#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

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
from cmk.plugins.emc.lib import DETECT_ISILON
from cmk.plugins.lib.df import df_check_filesystem_list, FILESYSTEM_DEFAULT_PARAMS, FSBlock

MIBI = 1024**2


def parse_emc_isilon_ifs(string_table: StringTable) -> FSBlock | None:
    for total, avail in string_table:
        # this check handles the cluster file system so there is only one
        return ("ifs", int(total) // MIBI, int(avail) // MIBI, 0)
    return None


snmp_section_emc_isilon_ifs = SimpleSNMPSection(
    name="emc_isilon_ifs",
    parse_function=parse_emc_isilon_ifs,
    detect=DETECT_ISILON,
    fetch=SNMPTree(
        base=".1.3.6.1.4.1.12124.1.3",
        oids=[
            "1",  # ifsTotalBytes
            "3",  # ifsAvailableBytes
        ],
    ),
)


def discover_emc_isilon_ifs(section: FSBlock) -> DiscoveryResult:
    yield Service(item="Cluster")


def check_emc_isilon_ifs(item: str, params: Mapping[str, Any], section: FSBlock) -> CheckResult:
    yield from df_check_filesystem_list(get_value_store(), "ifs", params, [section])


check_plugin_emc_isilon_ifs = CheckPlugin(
    name="emc_isilon_ifs",
    service_name="Filesystem %s",
    discovery_function=discover_emc_isilon_ifs,
    check_function=check_emc_isilon_ifs,
    check_ruleset_name="filesystem",
    check_default_parameters=FILESYSTEM_DEFAULT_PARAMS,
)
