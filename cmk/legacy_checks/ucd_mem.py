#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


from collections.abc import Mapping
from typing import Any

from cmk.agent_based.v2 import (
    CheckPlugin,
    CheckResult,
    DiscoveryResult,
    Result,
    Service,
    State,
)
from cmk.plugins.lib.memory import check_element
from cmk.plugins.ucd.agent_based.ucd_mem import Section

# .1.3.6.1.4.1.2021.4.2.0 swap      --> UCD-SNMP-MIB::memErrorName.0
# .1.3.6.1.4.1.2021.4.3.0 8388604   --> UCD-SNMP-MIB::MemTotalSwap.0
# .1.3.6.1.4.1.2021.4.4.0 8388604   --> UCD-SNMP-MIB::MemAvailSwap.0
# .1.3.6.1.4.1.2021.4.5.0 4003584   --> UCD-SNMP-MIB::MemTotalReal.0
# .1.3.6.1.4.1.2021.4.11.0 12233816 --> UCD-SNMP-MIB::MemTotalFree.0
# .1.3.6.1.4.1.2021.4.12.0 16000    --> UCD-SNMP-MIB::memMinimumSwap.0
# .1.3.6.1.4.1.2021.4.13.0 3163972  --> UCD-SNMP-MIB::memShared.0
# .1.3.6.1.4.1.2021.4.14.0 30364    --> UCD-SNMP-MIB::memBuffer.0
# .1.3.6.1.4.1.2021.4.15.0 10216780 --> UCD-SNMP-MIB::memCached.0
# .1.3.6.1.4.1.2021.4.100.0 0       --> UCD-SNMP-MIB::memSwapError.0
# .1.3.6.1.4.1.2021.4.101.0         --> UCD-SNMP-MIB::smemSwapErrorMsg.0


def discover_ucd_mem(section: Section) -> DiscoveryResult:
    if section:
        yield Service()


def check_ucd_mem(params: Mapping[str, Any], section: Section) -> CheckResult:
    error = section.get("error")
    if error and error != "swap":
        yield Result(state=State.WARN, summary=f"Error: {error}")

    # map legacy levels
    levels_ram = params.get("levels_ram") or params.get("levels")

    yield from check_element(
        "RAM",
        section["MemUsed"],
        section["MemTotal"],
        levels_ram,
        metric_name="mem_used",
        create_percent_metric=True,
    )

    swap_total = section.get("SwapTotal")
    swap_used = section.get("SwapUsed")
    if swap_total and swap_used is not None:
        yield from check_element(
            "Swap",
            swap_used,
            swap_total,
            params.get("levels_swap"),
            metric_name="swap_used",
        )

    total_total = section.get("TotalTotal")
    total_used = section.get("TotalUsed")
    if total_total is not None and total_used is not None:
        yield from check_element(
            "Total virtual memory",
            total_used,
            total_total,
            params.get("levels_virtual"),
        )

    # swap errors
    if section.get("error_swap", 0) != 0 and (error_swap_msg := section.get("error_swap_msg")):
        yield Result(
            state=State(int(params.get("swap_errors", 0))),
            summary=f"Swap error: {error_swap_msg}",
        )


# This check plug-in uses the migrated section in cmk/plugins/collection/agent_based/ucd_mem.py!
# Note: upon migration, move it into that file.
check_plugin_ucd_mem = CheckPlugin(
    name="ucd_mem",
    service_name="Memory",
    discovery_function=discover_ucd_mem,
    check_function=check_ucd_mem,
    check_ruleset_name="memory_simple_single",
    check_default_parameters={
        "levels": ("perc_used", (80.0, 90.0)),
        "swap_errors": 0,
    },
)
