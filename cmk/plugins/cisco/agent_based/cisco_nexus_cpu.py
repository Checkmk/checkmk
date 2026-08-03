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
    contains,
    DiscoveryResult,
    exists,
    get_value_store,
    Service,
    SimpleSNMPSection,
    SNMPTree,
    StringTable,
)
from cmk.plugins.lib.cpu_util import check_cpu_util

# .1.3.6.1.4.1.9.9.305.1.1.1.0 1 --> CISCO-SYSTEM-EXT-MIB::cseSysCPUUtilization.0


@dataclass(frozen=True)
class Section:
    cpu_perc: float


def discover_cisco_nexus_cpu(section: Section) -> DiscoveryResult:
    yield Service()


def check_cisco_nexus_cpu(params: Mapping[str, Any], section: Section) -> CheckResult:
    yield from check_cpu_util(
        util=section.cpu_perc,
        params=params,
        value_store=get_value_store(),
        this_time=time.time(),
    )


# Migration NOTE: Create a separate section, but a common check plug-in for
# tplink_cpu, hr_cpu, cisco_nexus_cpu, bintec_cpu, winperf_processor,
# lxc_container_cpu, docker_container_cpu.
# Migration via cmk/update_config.py!
def parse_cisco_nexus_cpu(string_table: StringTable) -> Section | None:
    if not string_table or not string_table[0][0]:
        return None
    return Section(float(string_table[0][0]))


snmp_section_cisco_nexus_cpu = SimpleSNMPSection(
    name="cisco_nexus_cpu",
    detect=all_of(
        contains(".1.3.6.1.2.1.1.1.0", "cisco"),
        contains(".1.3.6.1.2.1.1.1.0", "nx-os"),
        exists(".1.3.6.1.4.1.9.9.305.1.1.1.0"),
    ),
    fetch=SNMPTree(
        base=".1.3.6.1.4.1.9.9.305.1.1.1",
        oids=["0"],
    ),
    parse_function=parse_cisco_nexus_cpu,
)


check_plugin_cisco_nexus_cpu = CheckPlugin(
    name="cisco_nexus_cpu",
    service_name="CPU utilization",
    discovery_function=discover_cisco_nexus_cpu,
    check_function=check_cisco_nexus_cpu,
    check_ruleset_name="cpu_utilization_os",
    check_default_parameters={
        "util": (80.0, 90.0),
    },
)
