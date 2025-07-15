#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


# mypy: disable-error-code="arg-type"

from cmk.base.check_legacy_includes.uptime import check_uptime_seconds

from cmk.agent_based.legacy.v0_unstable import LegacyCheckDefinition
from cmk.agent_based.v2 import IgnoreResultsError, render

check_info = {}

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


def inventory_esx_vsphere_counters_uptime(parsed):
    if "sys.uptime" in parsed:
        return [(None, {})]
    return []


def check_esx_vsphere_counters_uptime(_no_item, params, parsed):
    if "sys.uptime" not in parsed:
        raise IgnoreResultsError("Counter data is missing")
    uptime = int(parsed["sys.uptime"][""][0][0][-1])
    if uptime < 0:
        raise IgnoreResultsError("Counter data is corrupt")
    return check_uptime_seconds(params, uptime)


check_info["esx_vsphere_counters.uptime"] = LegacyCheckDefinition(
    name="esx_vsphere_counters_uptime",
    service_name="Uptime",
    sections=["esx_vsphere_counters"],
    discovery_function=inventory_esx_vsphere_counters_uptime,
    check_function=check_esx_vsphere_counters_uptime,
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


def _parse_esx_vsphere_counters_swap(parsed):
    swap_values = {}

    for agent_key, key in (("mem.swapin", "in"), ("mem.swapout", "out"), ("mem.swapused", "used")):
        try:
            swap_values[key] = parsed[agent_key][""][0][0][0]
        except (KeyError, IndexError, TypeError, ValueError):
            continue

    return swap_values


def inventory_esx_vsphere_counters_swap(parsed):
    SWAP = _parse_esx_vsphere_counters_swap(parsed)

    if any(elem for elem in SWAP.values()):
        return [(None, {})]
    return []


def check_esx_vsphere_counters_swap(item, params, parsed):
    SWAP = _parse_esx_vsphere_counters_swap(parsed)

    for key in ("in", "out", "used"):
        if SWAP.get(key):
            value = render.bytes(float(SWAP[key]))
        else:
            value = "not available"

        yield 0, f"Swap {key}: {value}"


check_info["esx_vsphere_counters.swap"] = LegacyCheckDefinition(
    name="esx_vsphere_counters_swap",
    service_name="VMKernel Swap",
    sections=["esx_vsphere_counters"],
    discovery_function=inventory_esx_vsphere_counters_swap,
    check_function=check_esx_vsphere_counters_swap,
)
