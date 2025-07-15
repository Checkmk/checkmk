#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Mapping

from cmk.agent_based.legacy.v0_unstable import LegacyCheckDefinition, LegacyCheckResult
from cmk.agent_based.v2 import DiscoveryResult, Service, SNMPTree, StringTable
from cmk.base.check_legacy_includes.cpu_util import check_cpu_util
from cmk.plugins.lib.emc import DETECT_VPLEX

check_info = {}


def parse_emc_vplex_cpu(string_table: StringTable) -> Mapping[str, int]:
    return {director: int(util) for director, util in string_table}


def discover_emc_vplex_cpu(section: Mapping[str, int]) -> DiscoveryResult:
    yield from (Service(item=director) for director in section)


def check_emc_vplex_cpu(
    item: str, params: Mapping[str, object], section: Mapping[str, int]
) -> LegacyCheckResult:
    if (util := section.get(item)) is None:
        return
    yield from check_cpu_util(max(100 - util, 0), params)


check_info["emc_vplex_cpu"] = LegacyCheckDefinition(
    name="emc_vplex_cpu",
    detect=DETECT_VPLEX,
    fetch=SNMPTree(
        base=".1.3.6.1.4.1.1139.21.2.2",
        oids=["1.1.3", "3.1.1"],
    ),
    parse_function=parse_emc_vplex_cpu,
    service_name="CPU Utilization %s",
    discovery_function=discover_emc_vplex_cpu,
    check_function=check_emc_vplex_cpu,
    check_ruleset_name="cpu_utilization_multiitem",
    check_default_parameters={"levels": (90.0, 95.0)},
)
