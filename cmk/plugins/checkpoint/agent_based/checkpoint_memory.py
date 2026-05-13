#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# comNET GmbH, Fabian Binder

# .1.3.6.1.4.1.2620.1.6.7.4.3.0 8101654528 --> CHECKPOINT-MIB::memTotalReal
# .1.3.6.1.4.1.2620.1.6.7.4.4.0 2091094016 --> CHECKPOINT-MIB::memAvailReal

from collections.abc import Mapping

from cmk.agent_based.v2 import (
    CheckPlugin,
    CheckResult,
    DiscoveryResult,
    Service,
    SimpleSNMPSection,
    SNMPTree,
    StringTable,
)
from cmk.plugins.checkpoint.lib import DETECT
from cmk.plugins.lib.memory import check_element, MemoryLevels


def parse_checkpoint_memory(string_table: StringTable) -> StringTable:
    return string_table


def discover_checkpoint_memory(section: StringTable) -> DiscoveryResult:
    if section and len(section[0]) > 1:
        yield Service()


def check_checkpoint_memory(
    params: Mapping[str, MemoryLevels], section: StringTable
) -> CheckResult:
    mem_total_bytes, mem_used_bytes = map(int, section[0])
    yield from check_element(
        "Usage",
        mem_used_bytes,
        mem_total_bytes,
        params.get("levels"),
        metric_name="memory_used",
    )


snmp_section_checkpoint_memory = SimpleSNMPSection(
    name="checkpoint_memory",
    detect=DETECT,
    fetch=SNMPTree(
        base=".1.3.6.1.4.1.2620.1.6.7.4",
        oids=["3", "4"],
    ),
    parse_function=parse_checkpoint_memory,
)


check_plugin_checkpoint_memory = CheckPlugin(
    name="checkpoint_memory",
    service_name="Memory System",
    discovery_function=discover_checkpoint_memory,
    check_function=check_checkpoint_memory,
    check_ruleset_name="memory_simple_single",
    check_default_parameters={"levels": ("perc_used", (80.0, 90.0))},
)
