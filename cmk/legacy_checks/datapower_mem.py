#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# mypy: disable-error-code="explicit-any"

from collections.abc import Mapping
from typing import Any

from cmk.agent_based.v2 import (
    CheckPlugin,
    CheckResult,
    DiscoveryResult,
    Service,
    SimpleSNMPSection,
    SNMPTree,
    StringTable,
)
from cmk.plugins.datapower.lib import DETECT
from cmk.plugins.lib.memory import check_element


def discover_datapower_mem(section: StringTable) -> DiscoveryResult:
    if section:
        yield Service()


def check_datapower_mem(params: Mapping[str, Any], section: StringTable) -> CheckResult:
    mem_total_bytes = int(section[0][0]) * 1024
    mem_used_bytes = int(section[0][1]) * 1024

    yield from check_element(
        "Usage",
        mem_used_bytes,
        mem_total_bytes,
        params.get("levels"),
        metric_name="mem_used",
    )


def parse_datapower_mem(string_table: StringTable) -> StringTable:
    return string_table


snmp_section_datapower_mem = SimpleSNMPSection(
    name="datapower_mem",
    parse_function=parse_datapower_mem,
    detect=DETECT,
    fetch=SNMPTree(
        base=".1.3.6.1.4.1.14685.3.1.5",
        oids=["2", "3"],
    ),
)


check_plugin_datapower_mem = CheckPlugin(
    name="datapower_mem",
    service_name="Memory",
    discovery_function=discover_datapower_mem,
    check_function=check_datapower_mem,
    check_ruleset_name="memory_simple_single",
    check_default_parameters={"levels": ("perc_used", (80.0, 90.0))},
)
