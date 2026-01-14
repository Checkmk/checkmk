#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# mypy: disable-error-code="no-untyped-call"
# mypy: disable-error-code="no-untyped-def"


from cmk.agent_based.legacy.v0_unstable import LegacyCheckDefinition
from cmk.agent_based.v2 import any_of, contains, DiscoveryResult, Service, SNMPTree, StringTable
from cmk.base.check_legacy_includes.cpu_util import check_cpu_util

check_info = {}


def discover_hp_procurve_cpu(string_table: StringTable) -> DiscoveryResult:
    if len(string_table) == 1 and 0 <= int(string_table[0][0]) <= 100:
        yield Service()


def check_hp_procurve_cpu(item, params, info):
    try:
        util = int(info[0][0])
    except (IndexError, ValueError):
        return None

    if 0 <= util <= 100:
        return check_cpu_util(util, params)
    return None


def parse_hp_procurve_cpu(string_table: StringTable) -> StringTable:
    return string_table


check_info["hp_procurve_cpu"] = LegacyCheckDefinition(
    name="hp_procurve_cpu",
    parse_function=parse_hp_procurve_cpu,
    detect=any_of(
        contains(".1.3.6.1.2.1.1.2.0", ".11.2.3.7.11"),
        contains(".1.3.6.1.2.1.1.2.0", ".11.2.3.7.8"),
    ),
    fetch=SNMPTree(
        base=".1.3.6.1.4.1.11.2.14.11.5.1.9.6",
        oids=["1"],
    ),
    service_name="CPU utilization",
    discovery_function=discover_hp_procurve_cpu,
    check_function=check_hp_procurve_cpu,
    check_ruleset_name="cpu_utilization",
    check_default_parameters={"util": (80.0, 90.0)},
)
