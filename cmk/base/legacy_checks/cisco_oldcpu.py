#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


from cmk.agent_based.legacy.v0_unstable import LegacyCheckDefinition
from cmk.agent_based.v2 import (
    all_of,
    DiscoveryResult,
    exists,
    Service,
    SNMPTree,
    startswith,
    StringTable,
)
from cmk.base.check_legacy_includes.cpu_util import check_cpu_util

check_info = {}

# .1.3.6.1.4.1.9.2.1.57.0 13 --> OLD-CISCO-CPU-MIB::avgBusy1.0


def discover_cisco_oldcpu(section: StringTable) -> DiscoveryResult:
    if section and section[0][0]:
        yield Service()


def check_cisco_oldcpu(_no_item, params, info):
    return check_cpu_util(float(info[0][0]), params)


def parse_cisco_oldcpu(string_table: StringTable) -> StringTable:
    return string_table


check_info["cisco_oldcpu"] = LegacyCheckDefinition(
    name="cisco_oldcpu",
    parse_function=parse_cisco_oldcpu,
    detect=all_of(
        startswith(".1.3.6.1.2.1.1.2.0", ".1.3.6.1.4.1.9.1.1745"),
        exists(".1.3.6.1.4.1.9.9.109.1.1.1.1.2.*"),
        exists(".1.3.6.1.4.1.9.2.1.57.0"),
    ),
    fetch=SNMPTree(
        base=".1.3.6.1.4.1.9.2.1",
        oids=["57"],
    ),
    service_name="CPU utilization",
    discovery_function=discover_cisco_oldcpu,
    check_function=check_cisco_oldcpu,
    check_ruleset_name="cpu_utilization",
    check_default_parameters={"util": (80.0, 90.0)},
)
