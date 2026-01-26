#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# mypy: disable-error-code="no-untyped-call"

from collections.abc import Iterator, Mapping
from typing import Any

from cmk.agent_based.legacy.v0_unstable import LegacyCheckDefinition
from cmk.agent_based.v2 import (
    all_of,
    contains,
    DiscoveryResult,
    exists,
    Service,
    SNMPTree,
    StringTable,
)
from cmk.base.check_legacy_includes.cpu_util import check_cpu_util

check_info = {}

# .1.3.6.1.4.1.9.9.305.1.1.1.0 1 --> CISCO-SYSTEM-EXT-MIB::cseSysCPUUtilization.0


def discover_cisco_nexus_cpu(section: StringTable) -> DiscoveryResult:
    if section and section[0][0]:
        yield Service()


def check_cisco_nexus_cpu(
    _no_item: None, params: Mapping[str, Any], info: StringTable
) -> Iterator[tuple[int, str, list[Any]]]:
    yield from check_cpu_util(float(info[0][0]), params)


# Migration NOTE: Create a separate section, but a common check plug-in for
# tplink_cpu, hr_cpu, cisco_nexus_cpu, bintec_cpu, winperf_processor,
# lxc_container_cpu, docker_container_cpu.
# Migration via cmk/update_config.py!
def parse_cisco_nexus_cpu(string_table: StringTable) -> StringTable:
    return string_table


check_info["cisco_nexus_cpu"] = LegacyCheckDefinition(
    name="cisco_nexus_cpu",
    parse_function=parse_cisco_nexus_cpu,
    detect=all_of(
        contains(".1.3.6.1.2.1.1.1.0", "cisco"),
        contains(".1.3.6.1.2.1.1.1.0", "nx-os"),
        exists(".1.3.6.1.4.1.9.9.305.1.1.1.0"),
    ),
    fetch=SNMPTree(
        base=".1.3.6.1.4.1.9.9.305.1.1.1",
        oids=["0"],
    ),
    service_name="CPU utilization",
    discovery_function=discover_cisco_nexus_cpu,
    check_function=check_cisco_nexus_cpu,
    check_ruleset_name="cpu_utilization_os",
    check_default_parameters={
        "util": (80.0, 90.0),
    },
)
