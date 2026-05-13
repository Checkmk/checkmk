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
from cmk.plugins.avaya.lib import DETECT_AVAYA
from cmk.plugins.lib.cpu_util import check_cpu_util


def parse_avaya_88xx_cpu(string_table: StringTable) -> StringTable | None:
    return string_table or None


def discover_avaya_88xx_cpu(section: StringTable) -> DiscoveryResult:
    yield Service()


def check_avaya_88xx_cpu(params: Mapping[str, Any], section: StringTable) -> CheckResult:
    if not section:
        return
    yield from check_cpu_util(
        util=int(section[0][0]),
        params=params,
        value_store=get_value_store(),
        this_time=time.time(),
    )


snmp_section_avaya_88xx_cpu = SimpleSNMPSection(
    name="avaya_88xx_cpu",
    detect=DETECT_AVAYA,
    fetch=SNMPTree(
        base=".1.3.6.1.4.1.2272.1.1",
        oids=["20"],
    ),
    parse_function=parse_avaya_88xx_cpu,
)


check_plugin_avaya_88xx_cpu = CheckPlugin(
    name="avaya_88xx_cpu",
    service_name="CPU utilization",
    discovery_function=discover_avaya_88xx_cpu,
    check_function=check_avaya_88xx_cpu,
    check_ruleset_name="cpu_utilization",
    check_default_parameters={"util": (90.0, 95.0)},
)
