#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Mapping
from typing import Any

from cmk.agent_based.v2 import (
    AgentSection,
    CheckPlugin,
    CheckResult,
    DiscoveryResult,
    Result,
    Service,
    State,
    StringTable,
)
from cmk.plugins.lib import storeonce
from cmk.plugins.lib.df import FILESYSTEM_DEFAULT_PARAMS

# example output
#
# <<<storeonce_servicesets:sep(9)>>>
# [1]
# ServiceSet ID   1
# ServiceSet Name Service Set 1
# ServiceSet Alias        SET1
# Serial Number   CZ25132LTD01
# Software Version        3.15.1-1636.1
# Product Class   HPE StoreOnce 4700 Backup
# Capacity in bytes       75952808613643
# Free Space in bytes     53819324528395
# User Data Stored in bytes       305835970141743
# Size On Disk in bytes   19180587585836
# Deduplication Ratio     15.945078260668
# ServiceSet Health Level 1
# ServiceSet Health       OK
# ServiceSet Status       Running
# Replication Health Level        1
# Replication Health      OK
# Replication Status      Running
# Overall Health Level    1
# Overall Health  OK
# Overall Status  Running
# Housekeeping Health Level       1
# Housekeeping Health     OK
# Housekeeping Status     Running
# Primary Node    hpcz25132ltd
# Secondary Node  None
# Active Node     hpcz25132ltd
#
# In newer agent outputs 'capacity' has changed:
# cloudCapacityBytes  0
# cloudDiskBytes  0
# cloudReadWriteLicensedDiskBytes 0
# cloudFreeBytes  0
# cloudUserBytes  0
# localCapacityBytes  136721392009216
# localDiskBytes  47759419043899
# localFreeBytes  85220347674624
# localUserBytes  265622218292968
# combinedCapacityBytes   136721392009216
# combinedDiskBytes   47759419043899
# combinedFreeBytes   85220347674624
# combinedUserBytes   265622218292968


def parse_storeonce_servicesets(string_table: StringTable) -> storeonce.SectionServiceSets:
    return {
        data["ServiceSet ID"]: data
        for data in storeonce.parse_storeonce_servicesets(string_table).values()
    }


agent_section_storeonce_servicesets = AgentSection(
    name="storeonce_servicesets",
    parse_function=parse_storeonce_servicesets,
)


def discover_storeonce_servicesets(section: storeonce.SectionServiceSets) -> DiscoveryResult:
    yield from (Service(item=item) for item in section)


def check_storeonce_servicesets(item: str, section: storeonce.SectionServiceSets) -> CheckResult:
    if (values := section.get(item)) is None:
        return

    if "ServiceSet Alias" in values:
        yield Result(state=State.OK, summary="Alias: %s" % values["ServiceSet Alias"])
    elif "ServiceSet Name" in values:
        yield Result(state=State.OK, summary="Name: %s" % values["ServiceSet Name"])

    yield Result(
        state=State.OK,
        summary="Overall Status: %s, Overall Health: %s"
        % (
            values["Overall Status"],
            values["Overall Health"],
        ),
    )

    for component in [
        "ServiceSet Health",
        "Replication Health",
        "Housekeeping Health",
    ]:
        yield Result(
            state=storeonce.STATE_MAP[values["%s Level" % component]],
            notice=f"{component}: {values[component]}",
        )


check_plugin_storeonce_servicesets = CheckPlugin(
    name="storeonce_servicesets",
    service_name="ServiceSet %s Status",
    discovery_function=discover_storeonce_servicesets,
    check_function=check_storeonce_servicesets,
)


def check_storeonce_servicesets_capacity(
    item: str, params: Mapping[str, Any], section: storeonce.SectionServiceSets
) -> CheckResult:
    if (values := section.get(item)) is None:
        return
    yield from storeonce.check_storeonce_space(item, params, values)


check_plugin_storeonce_servicesets_capacity = CheckPlugin(
    name="storeonce_servicesets_capacity",
    service_name="ServiceSet %s Capacity",
    sections=["storeonce_servicesets"],
    discovery_function=discover_storeonce_servicesets,
    check_function=check_storeonce_servicesets_capacity,
    check_ruleset_name="filesystem",
    check_default_parameters=FILESYSTEM_DEFAULT_PARAMS,
)
