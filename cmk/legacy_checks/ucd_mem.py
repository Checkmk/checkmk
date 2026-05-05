#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


from collections.abc import Iterable, Mapping
from typing import Any

from cmk.agent_based.legacy.v0_unstable import LegacyCheckDefinition, LegacyResult
from cmk.legacy_includes.mem import check_memory_element
from cmk.plugins.collection.agent_based.ucd_mem import Section

check_info = {}

# FIXME
# The WATO group 'memory_simple' needs an item and the service_description should
# have a '%s'.  At the moment the current empty item '' and 'Memory' without '%s'
# works but is not consistent.  This will be fixed in the future.
# If we change this we loose history and parameter sets have to be adapted.

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


def discover_ucd_mem(parsed: Section) -> Iterable[tuple[None, dict[str, Any]]]:
    yield None, {}


def _check_memory_dict(meminfo: Section, params: Mapping[str, Any]) -> Iterable[LegacyResult]:
    yield check_memory_element(
        "RAM",
        meminfo["MemUsed"],
        meminfo["MemTotal"],
        params.get("levels_ram"),
        metric_name="mem_used",
        create_percent_metric=True,
    )

    if "SwapUsed" in meminfo and meminfo.get("SwapTotal"):
        yield check_memory_element(
            "Swap",
            meminfo["SwapUsed"],
            meminfo["SwapTotal"],
            params.get("levels_swap"),
            metric_name="swap_used",
        )

    if "TotalUsed" in meminfo and "TotalTotal" in meminfo:
        yield check_memory_element(
            "Total virtual memory",
            meminfo["TotalUsed"],
            meminfo["TotalTotal"],
            params.get("levels_virtual"),
        )


def check_ucd_mem(
    _no_item: None, params: dict[str, Any], parsed: Section
) -> Iterable[LegacyResult]:
    # general errors
    error = parsed["error"]
    if error and error != "swap":
        yield 1, "Error: %s" % error

    # map legacy levels
    if params.get("levels") is not None:
        params["levels_ram"] = params.pop("levels")

    yield from _check_memory_dict(parsed, params)

    # swap errors
    if "error_swap" in parsed:
        if parsed["error_swap"] != 0 and parsed["error_swap_msg"]:
            yield params.get("swap_errors", 0), "Swap error: %s" % parsed["error_swap_msg"]


# This check plug-in uses the migrated section in cmk/base/plugins/agent_based/ucd_mem.py!
# Note: upon migration, move it into that file.
check_info["ucd_mem"] = LegacyCheckDefinition(
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
