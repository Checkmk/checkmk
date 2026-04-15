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
    Result,
    Service,
    SimpleSNMPSection,
    SNMPTree,
    startswith,
    State,
    StringTable,
)
from cmk.plugins.lib.df import df_check_filesystem_list, FILESYSTEM_DEFAULT_PARAMS


def discover_nimble_volumes(section: StringTable) -> DiscoveryResult:
    for line in section:
        if line[4] == "1":
            yield Service(item=line[1])


def check_nimble_volumes(item: str, params: Mapping[str, Any], section: StringTable) -> CheckResult:
    for line in section:
        if line[1] == item:
            if line[4] == "0":
                yield Result(state=State.UNKNOWN, summary="Volume is offline!")
                continue
            total = int(line[2])
            free = total - int(line[3])
            yield from df_check_filesystem_list(
                get_value_store(),
                item,
                params,
                [(item, total, free, 0)],
                this_time=time.time(),
            )


def parse_nimble_volumes(string_table: StringTable) -> StringTable:
    return string_table


snmp_section_nimble_volumes = SimpleSNMPSection(
    name="nimble_volumes",
    detect=startswith(".1.3.6.1.2.1.1.2.0", ".1.3.6.1.4.1.37447.3.1"),
    fetch=SNMPTree(
        base=".1.3.6.1.4.1.37447.1.2.1",
        oids=["2", "3", "4", "6", "10"],
    ),
    parse_function=parse_nimble_volumes,
)


check_plugin_nimble_volumes = CheckPlugin(
    name="nimble_volumes",
    service_name="Volume %s",
    discovery_function=discover_nimble_volumes,
    check_function=check_nimble_volumes,
    check_ruleset_name="filesystem",
    check_default_parameters=FILESYSTEM_DEFAULT_PARAMS,
)
