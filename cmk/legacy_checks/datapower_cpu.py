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
from cmk.plugins.datapower.lib import DETECT
from cmk.plugins.lib.cpu_util import check_cpu_util


def discover_datapower_cpu(section: StringTable) -> DiscoveryResult:
    if section:
        yield Service()


def check_datapower_cpu(params: Mapping[str, Any], section: StringTable) -> CheckResult:
    util = int(section[0][0])
    yield from check_cpu_util(
        util=util,
        params=params,
        value_store=get_value_store(),
        this_time=time.time(),
    )


def parse_datapower_cpu(string_table: StringTable) -> StringTable:
    return string_table


snmp_section_datapower_cpu = SimpleSNMPSection(
    name="datapower_cpu",
    parse_function=parse_datapower_cpu,
    detect=DETECT,
    fetch=SNMPTree(
        base=".1.3.6.1.4.1.14685.3.1.14",
        oids=["2"],
    ),
)


check_plugin_datapower_cpu = CheckPlugin(
    name="datapower_cpu",
    service_name="CPU Utilization",
    discovery_function=discover_datapower_cpu,
    check_function=check_datapower_cpu,
    check_ruleset_name="cpu_utilization",
    check_default_parameters={"util": (80.0, 90.0)},
)
