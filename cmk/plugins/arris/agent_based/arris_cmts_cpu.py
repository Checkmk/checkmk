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
    equals,
    get_value_store,
    OIDEnd,
    Service,
    SimpleSNMPSection,
    SNMPTree,
    StringTable,
)
from cmk.plugins.lib.cpu_util import check_cpu_util


def discover_arris_cmts_cpu(section: StringTable) -> DiscoveryResult:
    for oid_id, cpu_id, _cpu_idle_util in section:
        # Sadly the cpu_id seams empty. Referring to
        # the MIB, its slot id
        # Fallback to the oid end
        yield Service(item=cpu_id or str(int(oid_id) - 1))


def check_arris_cmts_cpu(item: str, params: Mapping[str, Any], section: StringTable) -> CheckResult:
    for oid_id, cpu_id, cpu_idle_util in section:
        # see inventory function
        citem = cpu_id or str(int(oid_id) - 1)

        if citem == item:
            # We get the IDLE percentage, but need the usage
            cpu_util = 100.0 - float(cpu_idle_util)
            yield from check_cpu_util(
                util=cpu_util,
                params=params,
                value_store=get_value_store(),
                this_time=time.time(),
            )
            return


def parse_arris_cmts_cpu(string_table: StringTable) -> StringTable:
    return string_table


snmp_section_arris_cmts_cpu = SimpleSNMPSection(
    name="arris_cmts_cpu",
    detect=equals(".1.3.6.1.2.1.1.2.0", ".1.3.6.1.4.1.4998.2.1"),
    fetch=SNMPTree(
        base=".1.3.6.1.4.1.4998.1.1.5.3.1.1.1",
        oids=[OIDEnd(), "1", "8"],
    ),
    parse_function=parse_arris_cmts_cpu,
)


check_plugin_arris_cmts_cpu = CheckPlugin(
    name="arris_cmts_cpu",
    service_name="CPU utilization Module %s",
    discovery_function=discover_arris_cmts_cpu,
    check_function=check_arris_cmts_cpu,
    check_ruleset_name="cpu_utilization_multiitem",
    check_default_parameters={"levels": (90.0, 95.0)},
)
