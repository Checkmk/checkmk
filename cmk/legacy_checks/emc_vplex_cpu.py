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
from cmk.plugins.emc.lib import DETECT_VPLEX
from cmk.plugins.lib.cpu_util import check_cpu_util


def parse_emc_vplex_cpu(string_table: StringTable) -> Mapping[str, int]:
    return {director: int(util) for director, util in string_table}


def discover_emc_vplex_cpu(section: Mapping[str, int]) -> DiscoveryResult:
    yield from (Service(item=director) for director in section)


def check_emc_vplex_cpu(
    item: str, params: Mapping[str, Any], section: Mapping[str, int]
) -> CheckResult:
    if (util := section.get(item)) is None:
        return
    yield from check_cpu_util(
        util=max(100 - util, 0),
        params=params,
        value_store=get_value_store(),
        this_time=time.time(),
    )


snmp_section_emc_vplex_cpu = SimpleSNMPSection(
    name="emc_vplex_cpu",
    detect=DETECT_VPLEX,
    fetch=SNMPTree(
        base=".1.3.6.1.4.1.1139.21.2.2",
        oids=["1.1.3", "3.1.1"],
    ),
    parse_function=parse_emc_vplex_cpu,
)


check_plugin_emc_vplex_cpu = CheckPlugin(
    name="emc_vplex_cpu",
    service_name="CPU Utilization %s",
    discovery_function=discover_emc_vplex_cpu,
    check_function=check_emc_vplex_cpu,
    check_ruleset_name="cpu_utilization_multiitem",
    check_default_parameters={"levels": (90.0, 95.0)},
)
