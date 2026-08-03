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
    Metric,
    Result,
    Service,
    SimpleSNMPSection,
    SNMPTree,
    startswith,
    State,
    StringTable,
)
from cmk.plugins.lib.cpu_util import check_cpu_util

# Diese OIDs liefern nicht die LOAD, wie man annehmen koennte, sondern die
# UTILIZATION, da ausschliesslich die Auslastung der CPU beruecksichtigt wird.
# .1.3.6.1.4.1.272.4.17.4.1.1.15.1.0 5 --> BIANCA-BRICK-MIBRES-MIB::CpuLoadUser60s.1.0
# .1.3.6.1.4.1.272.4.17.4.1.1.16.1.0 1 --> BIANCA-BRICK-MIBRES-MIB::CpuLoadSystem60s.1.0
# .1.3.6.1.4.1.272.4.17.4.1.1.17.1.0 9 --> BIANCA-BRICK-MIBRES-MIB::CpuLoadStreams60s.1.0


def parse_bintec_cpu(string_table: StringTable) -> StringTable:
    return string_table


snmp_section_bintec_cpu = SimpleSNMPSection(
    name="bintec_cpu",
    parse_function=parse_bintec_cpu,
    detect=startswith(".1.3.6.1.2.1.1.2.0", ".1.3.6.1.4.1.272.4."),
    fetch=SNMPTree(
        base=".1.3.6.1.4.1.272.4.17.4.1.1",
        oids=["15", "16", "17"],
    ),
)


def discover_bintec_cpu(section: StringTable) -> DiscoveryResult:
    if section:
        yield Service()


def check_bintec_cpu(params: Mapping[str, Any], section: StringTable) -> CheckResult:
    user = float(section[0][0])
    system = float(section[0][1])
    streams = float(section[0][2])
    util = user + system + streams

    yield Result(state=State.OK, summary=f"user: {user:.1f}%")
    yield Result(state=State.OK, summary=f"system: {system:.1f}%")
    yield Result(state=State.OK, summary=f"streams: {streams:.1f}%")
    yield Metric("streams", streams)

    yield from check_cpu_util(
        util=util,
        params=params,
        value_store=get_value_store(),
        this_time=time.time(),
    )


# Migration NOTE: Create a separate section, but a common check plug-in for
# tplink_cpu, hr_cpu, cisco_nexus_cpu, bintec_cpu, winperf_processor,
# lxc_container_cpu, docker_container_cpu.
# Migration via cmk/update_config.py!
check_plugin_bintec_cpu = CheckPlugin(
    name="bintec_cpu",
    service_name="CPU utilization",
    discovery_function=discover_bintec_cpu,
    check_function=check_bintec_cpu,
    check_ruleset_name="cpu_utilization_os",
    check_default_parameters={},
)
