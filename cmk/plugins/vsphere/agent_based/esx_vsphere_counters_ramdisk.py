#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Mapping, Sequence
from typing import Any, Final

from cmk.agent_based.v2 import (
    CheckPlugin,
    CheckResult,
    DiscoveryResult,
    get_value_store,
    Result,
    RuleSetType,
    State,
)
from cmk.plugins.lib.df import df_check_filesystem_list, df_discovery, FILESYSTEM_DEFAULT_PARAMS
from cmk.plugins.vsphere.lib.esx_vsphere import SectionCounter

# We assume that all ramdisks have the same size (in mb) on all hosts
# -> To get size infos about unknown ramdisks, connect to the ESX host via
#    SSH and check the size of the disk via "du" command
ESX_VSPHERE_COUNTERS_RAMDISK_SIZES: Final = {
    "root": 32,
    "etc": 28,
    "tmp": 192,
    "hostdstats": 319,
    "snmptraps": 1,
    "upgradescratch": 300,
    "ibmscratch": 300,
    "sfcbtickets": 1,
}


def _instance_to_item(instance: str) -> str | None:
    return (
        instance.split("/")[-1]
        if instance.startswith("host/system/kernel/kmanaged/visorfs/")
        else None
    )


def discover_esx_vsphere_counters_ramdisk(
    params: Sequence[Mapping[str, Any]], section: SectionCounter
) -> DiscoveryResult:
    yield from df_discovery(
        params,
        [
            name
            for instance in section.get("sys.resourceMemConsumed", {})
            if (name := _instance_to_item(instance)) is not None
        ],
    )


def check_esx_vsphere_counters_ramdisk(
    item: str, params: Mapping[str, Any], section: SectionCounter
) -> CheckResult:
    if (mem_counter := section.get("sys.resourceMemConsumed")) is None:
        return

    ramdisks = []
    for instance, counter in mem_counter.items():
        if (name := _instance_to_item(instance)) is None:
            continue

        try:
            size_mb = ESX_VSPHERE_COUNTERS_RAMDISK_SIZES[name]
        except KeyError:
            if item == name:
                yield Result(state=State.UNKNOWN, summary=f"Unhandled ramdisk found ({name})")
                return
            continue

        used_mb = float(counter[0][0][-1]) / 1000.0
        avail_mb = size_mb - used_mb
        ramdisks.append((name, size_mb, avail_mb, 0))

    yield from df_check_filesystem_list(
        value_store=get_value_store(),
        item=item,
        params=params,
        fslist_blocks=ramdisks,
    )


check_plugin_esx_vsphere_counters_ramdisk = CheckPlugin(
    name="esx_vsphere_counters_ramdisk",
    service_name="Ramdisk %s",
    sections=["esx_vsphere_counters"],
    discovery_function=discover_esx_vsphere_counters_ramdisk,
    discovery_ruleset_name="filesystem_groups",
    discovery_ruleset_type=RuleSetType.ALL,
    discovery_default_parameters={"groups": []},
    check_function=check_esx_vsphere_counters_ramdisk,
    check_ruleset_name="filesystem",
    check_default_parameters=FILESYSTEM_DEFAULT_PARAMS,
)
