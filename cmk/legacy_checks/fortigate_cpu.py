#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# mypy: disable-error-code="explicit-any"

import time
from collections.abc import Mapping
from typing import Any

from cmk.agent_based.v2 import (
    all_of,
    CheckPlugin,
    CheckResult,
    contains,
    DiscoveryResult,
    exists,
    get_value_store,
    not_exists,
    Result,
    Service,
    SimpleSNMPSection,
    SNMPTree,
    StringTable,
)
from cmk.plugins.lib.cpu_util import check_cpu_util

Section = StringTable


def parse_fortigate_cpu(string_table: StringTable) -> Section | None:
    return string_table or None


def discover_fortigate_cpu(section: Section) -> DiscoveryResult:
    yield Service()


def check_fortigate_cpu(params: Mapping[str, Any], section: Section) -> CheckResult:
    num_cpus = len(section)
    util = sum(float(raw_util) for raw_util, *_rest in section) / num_cpus

    for element in check_cpu_util(
        util=util,
        params=params,
        value_store=get_value_store(),
        this_time=time.time(),
    ):
        yield (
            Result(state=element.state, summary=f"{element.summary} at {num_cpus} CPUs")
            if isinstance(element, Result)
            else element
        )


snmp_section_fortigate_cpu_base = SimpleSNMPSection(
    name="fortigate_cpu_base",
    detect=all_of(
        contains(".1.3.6.1.2.1.1.2.0", ".1.3.6.1.4.1.12356.101.1"),
        exists(".1.3.6.1.4.1.12356.101.4.1.3.0"),
    ),
    # uses mib FORTINET-FORTIGATE-MIB,
    fetch=SNMPTree(
        base=".1.3.6.1.4.1.12356.101.4.1",
        oids=["3"],
    ),
    parse_function=parse_fortigate_cpu,
)


check_plugin_fortigate_cpu_base = CheckPlugin(
    name="fortigate_cpu_base",
    service_name="CPU utilization",
    discovery_function=discover_fortigate_cpu,
    check_function=check_fortigate_cpu,
    check_ruleset_name="cpu_utilization",
    check_default_parameters={"util": (80.0, 90.0)},
)


snmp_section_fortigate_cpu = SimpleSNMPSection(
    name="fortigate_cpu",
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
    parse_function=parse_fortigate_cpu,
)


check_plugin_fortigate_cpu = CheckPlugin(
    name="fortigate_cpu",
    service_name="CPU utilization",
    discovery_function=discover_fortigate_cpu,
    check_function=check_fortigate_cpu,
    check_ruleset_name="cpu_utilization",
    check_default_parameters={"util": (80.0, 90.0)},
)
