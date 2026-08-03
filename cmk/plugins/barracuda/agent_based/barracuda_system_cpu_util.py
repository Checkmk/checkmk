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
from cmk.plugins.barracuda.lib import DETECT_BARRACUDA
from cmk.plugins.lib.cpu_util import check_cpu_util

# .1.3.6.1.4.1.20632.2.13 3

# Suggested by customer


def discover_barracuda_system_cpu_util(section: StringTable) -> DiscoveryResult:
    yield Service()


def check_barracuda_system_cpu_util(params: Mapping[str, Any], section: StringTable) -> CheckResult:
    yield from check_cpu_util(
        util=int(section[0][0]),
        params=params,
        value_store=get_value_store(),
        this_time=time.time(),
    )


def parse_barracuda_system_cpu_util(string_table: StringTable) -> StringTable | None:
    return string_table or None


snmp_section_barracuda_system_cpu_util = SimpleSNMPSection(
    name="barracuda_system_cpu_util",
    detect=DETECT_BARRACUDA,
    # The barracuda spam firewall does not response or returns a timeout error
    # executing 'snmpwalk' on whole tables. But we can workaround here specifying
    # all needed OIDs. Then we can use 'snmpget' and 'snmpwalk' on these single OIDs.
    fetch=SNMPTree(
        base=".1.3.6.1.4.1.20632.2",
        oids=["13"],
    ),
    parse_function=parse_barracuda_system_cpu_util,
)


check_plugin_barracuda_system_cpu_util = CheckPlugin(
    name="barracuda_system_cpu_util",
    service_name="CPU utilization",
    discovery_function=discover_barracuda_system_cpu_util,
    check_function=check_barracuda_system_cpu_util,
    check_ruleset_name="cpu_utilization",
    check_default_parameters={"util": (80.0, 90.0)},
)
