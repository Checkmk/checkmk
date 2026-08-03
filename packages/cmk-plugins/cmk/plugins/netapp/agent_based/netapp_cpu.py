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
    DiscoveryResult,
    exists,
    get_value_store,
    Service,
    SimpleSNMPSection,
    SNMPTree,
    startswith,
    StringTable,
)
from cmk.plugins.lib.cpu_util import check_cpu_util


def check_netapp_cpu(params: Mapping[str, Any], section: StringTable) -> CheckResult:
    util = float(section[0][0])
    yield from check_cpu_util(
        util=util,
        params=params,
        value_store=get_value_store(),
        this_time=time.time(),
    )


def parse_netapp_cpu(string_table: StringTable) -> StringTable | None:
    return string_table or None


def discover_netapp_cpu(section: StringTable) -> DiscoveryResult:
    yield Service()


snmp_section_netapp_cpu = SimpleSNMPSection(
    name="netapp_cpu",
    detect=all_of(
        startswith(".1.3.6.1.2.1.1.1.0", "NetApp Release"), exists(".1.3.6.1.4.1.789.1.2.1.3.0")
    ),
    fetch=SNMPTree(
        base=".1.3.6.1.4.1.789.1.2.1",
        oids=["3"],
    ),
    parse_function=parse_netapp_cpu,
)


check_plugin_netapp_cpu = CheckPlugin(
    name="netapp_cpu",
    service_name="CPU utilization",
    discovery_function=discover_netapp_cpu,
    check_function=check_netapp_cpu,
    check_ruleset_name="cpu_utilization",
    check_default_parameters={"util": (80.0, 90.0)},
)
