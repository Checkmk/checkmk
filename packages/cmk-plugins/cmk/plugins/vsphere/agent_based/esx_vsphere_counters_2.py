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
    IgnoreResultsError,
    render,
    Result,
    Service,
    State,
)
from cmk.plugins.lib import uptime
from cmk.plugins.vsphere.lib.esx_vsphere import SectionCounter

# Example output:
# <<<esx_vsphere_counters:sep(124)>>>
# net.broadcastRx|vmnic0|11|number
# net.broadcastRx||11|number
# net.broadcastTx|vmnic0|0|number
# net.broadcastTx||0|number
# net.bytesRx|vmnic0|3820|kiloBytesPerSecond
# net.bytesRx|vmnic1|0|kiloBytesPerSecond
# net.bytesRx|vmnic2|0|kiloBytesPerSecond
# net.bytesRx|vmnic3|0|kiloBytesPerSecond
# net.bytesRx||3820|kiloBytesPerSecond
# net.bytesTx|vmnic0|97|kiloBytesPerSecond
# net.bytesTx|vmnic1|0|kiloBytesPerSecond
# net.bytesTx|vmnic2|0|kiloBytesPerSecond
# net.bytesTx|vmnic3|0|kiloBytesPerSecond
# net.bytesTx||97|kiloBytesPerSecond
# net.droppedRx|vmnic0|0|number
# net.droppedRx|vmnic1|0|number
# net.droppedRx|vmnic2|0|number
# net.droppedRx|vmnic3|0|number
# net.droppedRx||0|number
# net.droppedTx|vmnic0|0|number
# net.droppedTx|vmnic1|0|number
# ...
# sys.uptime||630664|second


# .
#   .--Uptime--------------------------------------------------------------.
#   |                  _   _       _   _                                   |
#   |                 | | | |_ __ | |_(_)_ __ ___   ___                    |
#   |                 | | | | '_ \| __| | '_ ` _ \ / _ \                   |
#   |                 | |_| | |_) | |_| | | | | | |  __/                   |
#   |                  \___/| .__/ \__|_|_| |_| |_|\___|                   |
#   |                       |_|                                            |
#   '----------------------------------------------------------------------'


def discover_esx_vsphere_counters_uptime(section: SectionCounter) -> DiscoveryResult:
    if "sys.uptime" in section:
        yield Service()


def check_esx_vsphere_counters_uptime(
    params: Mapping[str, Any], section: SectionCounter
) -> CheckResult:
    if "sys.uptime" not in section:
        raise IgnoreResultsError("Counter data is missing")
    uptime_sec = int(section["sys.uptime"][""][0][0][-1])
    if uptime_sec < 0:
        raise IgnoreResultsError("Counter data is corrupt")
    yield from uptime.check(params, uptime.Section(uptime_sec=uptime_sec, message=None))


check_plugin_esx_vsphere_counters_uptime = CheckPlugin(
    name="esx_vsphere_counters_uptime",
    service_name="Uptime",
    sections=["esx_vsphere_counters"],
    discovery_function=discover_esx_vsphere_counters_uptime,
    check_function=check_esx_vsphere_counters_uptime,
    check_default_parameters={},
    check_ruleset_name="uptime",
)


#   .--swap----------------------------------------------------------------.
#   |                                                                      |
#   |                       _____      ____ _ _ __                         |
#   |                      / __\ \ /\ / / _` | '_ \                        |
#   |                      \__ \\ V  V / (_| | |_) |                       |
#   |                      |___/ \_/\_/ \__,_| .__/                        |
#   |                                        |_|                           |
#   +----------------------------------------------------------------------+


def _parse_esx_vsphere_counters_swap(parsed: SectionCounter) -> Mapping[str, str]:
    swap_values = {}

    for agent_key, key in (("mem.swapin", "in"), ("mem.swapout", "out"), ("mem.swapused", "used")):
        try:
            swap_values[key] = parsed[agent_key][""][0][0][0]
        except (KeyError, IndexError, TypeError, ValueError):
            continue

    return swap_values


def inventory_esx_vsphere_counters_swap(section: SectionCounter) -> DiscoveryResult:
    SWAP = _parse_esx_vsphere_counters_swap(section)

    if any(elem for elem in SWAP.values()):
        yield Service()


def check_esx_vsphere_counters_swap(section: SectionCounter) -> CheckResult:
    swap = _parse_esx_vsphere_counters_swap(section)

    for key, value in swap.items():
        if value and key in {"in", "out", "used"}:
            yield Result(state=State.OK, summary=f"Swap {key}: {render.bytes(float(value))}")


check_plugin_esx_vsphere_counters_swap = CheckPlugin(
    name="esx_vsphere_counters_swap",
    service_name="VMKernel Swap",
    sections=["esx_vsphere_counters"],
    discovery_function=inventory_esx_vsphere_counters_swap,
    check_function=check_esx_vsphere_counters_swap,
)
