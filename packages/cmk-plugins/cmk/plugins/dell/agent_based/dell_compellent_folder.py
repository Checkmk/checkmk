#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# mypy: disable-error-code="explicit-any"

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
from cmk.plugins.dell.lib import DETECT_DELL_COMPELLENT
from cmk.plugins.lib.df import df_check_filesystem_list, FILESYSTEM_DEFAULT_PARAMS


def discover_dell_compellent_folder(section: StringTable) -> DiscoveryResult:
    for line in section:
        if line[1] and float(line[1]) != 0:
            yield Service(item=line[0])


def check_dell_compellent_folder(
    item: str, params: Mapping[str, Any], section: StringTable
) -> CheckResult:
    for number, total, used in section:
        if number == item:
            # sizes delivered in GiB
            total_mb = float(total) * 1024
            free_mb = total_mb - float(used) * 1024
            yield from df_check_filesystem_list(
                get_value_store(),
                item,
                params,
                [(item, total_mb, free_mb, 0)],
                this_time=time.time(),
            )


def parse_dell_compellent_folder(string_table: StringTable) -> StringTable:
    return string_table


snmp_section_dell_compellent_folder = SimpleSNMPSection(
    name="dell_compellent_folder",
    detect=DETECT_DELL_COMPELLENT,
    fetch=SNMPTree(
        base=".1.3.6.1.4.1.674.11000.2000.500.1.2.32.1",
        oids=["2", "5", "6"],
    ),
    parse_function=parse_dell_compellent_folder,
)

check_plugin_dell_compellent_folder = CheckPlugin(
    name="dell_compellent_folder",
    service_name="Folder %s",
    discovery_function=discover_dell_compellent_folder,
    check_function=check_dell_compellent_folder,
    check_ruleset_name="filesystem",
    check_default_parameters=FILESYSTEM_DEFAULT_PARAMS,
)
