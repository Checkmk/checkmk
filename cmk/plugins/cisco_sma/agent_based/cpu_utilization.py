#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import time
from collections.abc import Mapping, MutableMapping

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
from cmk.plugins.lib.cpu_util import check_cpu_util

from .detect import DETECT_CISCO_SMA


def _parse_cpu_utilization(string_table: StringTable) -> float | None:
    return float(string_table[0][0]) if string_table else None


snmp_section_cpu_utilization = SimpleSNMPSection(
    name="cisco_sma_cpu_utilization",
    detect=DETECT_CISCO_SMA,
    fetch=SNMPTree(
        base=".1.3.6.1.4.1.15497.1.1.1",
        oids=["2"],
    ),
    parse_function=_parse_cpu_utilization,
    supersedes=["hr_cpu"],
)


def _discover_cpu_utilization(section: float) -> DiscoveryResult:
    yield Service()


def _check_cpu_utilization(params: Mapping[str, object], section: float) -> CheckResult:
    yield from _check_cpu_utilization_testable(
        util=section,
        params=params,
        value_store=get_value_store(),
        this_time=time.time(),
    )


def _check_cpu_utilization_testable(
    util: float,
    params: Mapping[str, object],
    value_store: MutableMapping[str, object],
    this_time: float,
) -> CheckResult:
    yield from check_cpu_util(
        util=util,
        params=params,
        value_store=value_store,
        this_time=this_time,
    )


check_plugin_cpu_utilization = CheckPlugin(
    name="cisco_sma_cpu_utilization",
    service_name="CPU utilization",
    discovery_function=_discover_cpu_utilization,
    check_function=_check_cpu_utilization,
    check_ruleset_name="cpu_utilization_os",
    check_default_parameters={
        "util": (70.0, 80.0),
    },
)
