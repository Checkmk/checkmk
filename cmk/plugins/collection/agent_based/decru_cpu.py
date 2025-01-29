#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


from cmk.agent_based.v2 import (
    CheckPlugin,
    CheckResult,
    DiscoveryResult,
    Metric,
    Result,
    Service,
    SimpleSNMPSection,
    SNMPTree,
    State,
    StringTable,
)
from cmk.plugins.lib.decru import DETECT_DECRU


def inventory_decru_cpu(section: StringTable) -> DiscoveryResult:
    if len(section) == 5:
        yield Service()


def check_decru_cpu(section: StringTable) -> CheckResult:
    user, nice, system, interrupt, idle = (float(x[0]) / 10.0 for x in section)
    user += nice

    yield Result(
        state=State.OK,
        summary=f"user {user:.0f}%, sys {system:.0f}%, interrupt {interrupt:.0f}%, idle {idle:.0f}%",
    )
    yield Metric("user", user)
    yield Metric("system", system)
    yield Metric("interrupt", interrupt)


def parse_decru_cpu(string_table: StringTable) -> StringTable:
    return string_table


snmp_section_decru_cpu = SimpleSNMPSection(
    name="decru_cpu",
    detect=DETECT_DECRU,
    fetch=SNMPTree(
        base=".1.3.6.1.4.1.12962.1.1",
        oids=["8"],
    ),
    parse_function=parse_decru_cpu,
)
check_plugin_decru_cpu = CheckPlugin(
    name="decru_cpu",
    service_name="CPU utilization",
    discovery_function=inventory_decru_cpu,
    check_function=check_decru_cpu,
)
