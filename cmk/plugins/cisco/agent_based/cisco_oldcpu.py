#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# mypy: disable-error-code="explicit-any"

import time
from collections.abc import Mapping
from dataclasses import dataclass
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

# .1.3.6.1.4.1.9.2.1.57.0 13 --> OLD-CISCO-CPU-MIB::avgBusy1.0


@dataclass(frozen=True)
class Section:
    cpu_perc: float


def discover_cisco_oldcpu(section: Section) -> DiscoveryResult:
    yield Service()


def check_cisco_oldcpu(params: Mapping[str, Any], section: Section) -> CheckResult:
    yield from check_cpu_util(
        util=section.cpu_perc,
        params=params,
        value_store=get_value_store(),
        this_time=time.time(),
    )


def parse_cisco_oldcpu(string_table: StringTable) -> Section | None:
    if not string_table or not string_table[0][0]:
        return None
    return Section(float(string_table[0][0]))


snmp_section_cisco_oldcpu = SimpleSNMPSection(
    name="cisco_oldcpu",
    detect=all_of(
        startswith(".1.3.6.1.2.1.1.2.0", ".1.3.6.1.4.1.9.1.1745"),
        exists(".1.3.6.1.4.1.9.9.109.1.1.1.1.2.*"),
        exists(".1.3.6.1.4.1.9.2.1.57.0"),
    ),
    fetch=SNMPTree(
        base=".1.3.6.1.4.1.9.2.1",
        oids=["57"],
    ),
    parse_function=parse_cisco_oldcpu,
)


check_plugin_cisco_oldcpu = CheckPlugin(
    name="cisco_oldcpu",
    service_name="CPU utilization",
    discovery_function=discover_cisco_oldcpu,
    check_function=check_cisco_oldcpu,
    check_ruleset_name="cpu_utilization",
    check_default_parameters={"util": (80.0, 90.0)},
)
