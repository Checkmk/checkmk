#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


from cmk.agent_based.legacy.v0_unstable import LegacyCheckDefinition
from cmk.agent_based.v2 import (
    all_of,
    contains,
    DiscoveryResult,
    exists,
    not_exists,
    Service,
    SNMPTree,
    StringTable,
)
from cmk.base.check_legacy_includes.cpu_util import check_cpu_util

check_info = {}


def parse_fortigate_cpu(string_table: StringTable) -> StringTable | None:
    return string_table or None


def discover_fortigate_cpu(string_table: StringTable) -> DiscoveryResult:
    yield Service()


def check_fortigate_cpu(item, params, info):
    if (num_cpus := len(info)) == 0:
        return None

    util = sum(float(raw_util) for raw_util, *_rest in info) / num_cpus

    state, infotext, perfdata = next(check_cpu_util(util, params))
    infotext += " at %d CPUs" % num_cpus

    return state, infotext, perfdata


check_info["fortigate_cpu_base"] = LegacyCheckDefinition(
    name="fortigate_cpu_base",
    parse_function=parse_fortigate_cpu,
    detect=all_of(
        contains(".1.3.6.1.2.1.1.2.0", ".1.3.6.1.4.1.12356.101.1"),
        exists(".1.3.6.1.4.1.12356.101.4.1.3.0"),
    ),
    # uses mib FORTINET-FORTIGATE-MIB,
    fetch=SNMPTree(
        base=".1.3.6.1.4.1.12356.101.4.1",
        oids=["3"],
    ),
    service_name="CPU utilization",
    discovery_function=discover_fortigate_cpu,
    check_function=check_fortigate_cpu,
    check_ruleset_name="cpu_utilization",
    check_default_parameters={"util": (80.0, 90.0)},
)

check_info["fortigate_cpu"] = LegacyCheckDefinition(
    name="fortigate_cpu",
    parse_function=parse_fortigate_cpu,
    detect=all_of(
        contains(".1.3.6.1.2.1.1.2.0", ".1.3.6.1.4.1.12356.101.1"),
        exists(".1.3.6.1.4.1.12356.1.8.0"),
        not_exists(".1.3.6.1.4.1.12356.101.4.1.3.0"),
    ),
    # uses mib FORTINET-MIB-280,
    fetch=SNMPTree(
        base=".1.3.6.1.4.1.12356.1",
        oids=["8"],
    ),
    service_name="CPU utilization",
    discovery_function=discover_fortigate_cpu,
    check_function=check_fortigate_cpu,
    check_ruleset_name="cpu_utilization",
    check_default_parameters={"util": (80.0, 90.0)},
)
