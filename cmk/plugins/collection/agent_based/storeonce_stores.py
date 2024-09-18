#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Mapping

from cmk.agent_based.v1 import check_levels as check_levels_v1
from cmk.agent_based.v2 import (
    AgentSection,
    CheckPlugin,
    CheckResult,
    DiscoveryResult,
    render,
    Result,
    Service,
    State,
    StringTable,
)
from cmk.plugins.lib import storeonce

Section = Mapping[str, Mapping[str, str]]

# <<<storeonce_stores:sep(9)>>>
# [1/0]
# Store ID        0
# Name    VM_WinSrv_Store
# Description     Catalyst Store for Windows based Server
# ServiceSet ID   1
# Creation Time UTC       1434446799
# Health Level    1
# Health  OK
# Status  Online
# Version 2
# Number Of Catalyst Items        274
# User Data Stored        1467.568399314
# Size On Disk    604.827284898
# Dedupe Ratio    2.4
# Dedupe Ratio    2.4
# Creation On     2015-06-16T09:26:39Z
# Last Modified   2015-06-16T09:26:39Z
# primaryTransferPolicy   0
# primaryTransferPolicyString     High Bandwidth
# secondaryTransferPolicy 1
# secondaryTransferPolicyString   Low Bandwidth
# userDataSizeLimitBytes  0
# dedupedDataSizeOnDiskLimitBytes 0
# dataJobRetentionDays    90
# inboundCopyJobRetentionDays     90
# outboundCopyJobRetentionDays    90
# supportStorageModeVariableBlockDedupe   true
# supportStorageModeFixedBlockDedupe      true
# supportStorageModeNoDedupe      true
# supportWriteSparse      false
# supportWriteInPlace     false
# supportRawReadWrite     true
# supportMultipleObjectOpeners    true
# supportMultipleObjectWrites     false
# supportCloneExtent      true
# userBytes       1467568399314
# diskBytes       604827284898
# numItems        274
# numDataJobs     2536
# numOriginCopyJobs       0
# numDestinationCopyJobs  0
# Is online       true
# is store encrypted      false
# secure erase mode       0
# secure erase mode description   Secure_Erase_NoPassCount
# isTeamed        false
# teamUUID        0000014DFBB121BB2954110834BAD600
# numTeamMembers  0


def parse_storeonce_stores(string_table: StringTable) -> Section:
    return {
        "ServiceSet {} Store {}".format(data["ServiceSet ID"], data["Name"]): data
        for data in storeonce.parse_storeonce_servicesets(string_table).values()
    }


agent_section_storeonce_stores = AgentSection(
    name="storeonce_stores",
    parse_function=parse_storeonce_stores,
)


def discover_storeonce_stores(section: Section) -> DiscoveryResult:
    yield from (Service(item=item) for item in section)


def check_storeonce_stores(item: str, section: Section) -> CheckResult:
    if (values := section.get(item)) is None:
        return

    yield Result(
        state=storeonce.STATE_MAP[values["Health Level"]],
        summary="Status: %s" % values["Status"],
    )

    yield from check_levels_v1(
        float(values["diskBytes"]), metric_name="data_size", label="Size", render_func=render.bytes
    )

    if "Dedupe Ratio" in values:
        yield from check_levels_v1(
            float(values["Dedupe Ratio"]), metric_name="dedup_rate", label="Dedup ratio"
        )

    description = values.get("Description")
    if description:
        yield Result(state=State.OK, summary="Description: %s" % description)


check_plugin_storeonce_stores = CheckPlugin(
    name="storeonce_stores",
    service_name="%s",
    discovery_function=discover_storeonce_stores,
    check_function=check_storeonce_stores,
)
