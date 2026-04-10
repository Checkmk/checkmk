#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import time
from collections.abc import Mapping, MutableMapping
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
from cmk.plugins.lib.cpu_util import check_cpu_util
from cmk.plugins.tplink.lib import DETECT_TPLINK


def parse_tplink_cpu(string_table: StringTable) -> StringTable:
    return string_table


snmp_section_tplink_cpu = SimpleSNMPSection(
    name="tplink_cpu",
    detect=DETECT_TPLINK,
    fetch=SNMPTree(
        base=".1.3.6.1.4.1.11863.6.4.1.1.1.1",
        oids=["2"],
    ),
    parse_function=parse_tplink_cpu,
)


def discover_tplink_cpu(section: StringTable) -> DiscoveryResult:
    if len(section) >= 1:
        yield Service()


def check_tplink_cpu_(
    params: Mapping[str, Any], section: StringTable, value_store: MutableMapping[str, Any]
) -> CheckResult:

    num_cpus = 0
    util = 0.0
    cores: list[tuple[str, int]] = []

    for line in section:
        core_util = int(line[0])
        cores.append((f"core{num_cpus}", core_util))
        util += core_util
        num_cpus += 1

    if num_cpus == 0:
        return

    util = float(util) / num_cpus
    yield from check_cpu_util(
        util=util,
        params=params,
        cores=cores,
        value_store=value_store,
        this_time=time.time(),
    )


def check_tplink_cpu(params: Mapping[str, Any], section: StringTable) -> CheckResult:
    yield from check_tplink_cpu_(params, section, get_value_store())


check_plugin_tplink_cpu = CheckPlugin(
    name="tplink_cpu",
    service_name="CPU utilization",
    discovery_function=discover_tplink_cpu,
    check_function=check_tplink_cpu,
    check_ruleset_name="cpu_utilization_os",
    check_default_parameters={},
)
