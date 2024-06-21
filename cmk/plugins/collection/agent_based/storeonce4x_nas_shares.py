#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
import json
from collections.abc import Mapping
from typing import Any

from cmk.agent_based.v2 import (
    AgentSection,
    CheckPlugin,
    CheckResult,
    DiscoveryResult,
    get_value_store,
    Metric,
    render,
    Result,
    Service,
    State,
    StringTable,
)
from cmk.plugins.lib.df import df_check_filesystem_list, FILESYSTEM_DEFAULT_PARAMS

Store = Mapping[str, Any]
Section = Mapping[str, Store]

def parse_storeonce4x_nas_shares(string_table: StringTable) -> Section:
    return {
        "%d - %s" % (elem["id"], elem["name"]): elem  #
        for elem in json.loads(string_table[0][0])["members"]
    }

agent_section_storeonce4x_cat_stores = AgentSection(
    name="storeonce4x_nas_shares",
    parse_function=parse_storeonce4x_nas_shares,
)


def discover_storeonce4x_nas_shares(section: Section) -> DiscoveryResult:
    yield from (Service(item=k) for k in section)


def check_storeonce4x_nas_shares(
    item: str, params: Mapping[str, Any], section: Section
) -> CheckResult:
    if not (share := section.get(item)):
        return

    yield Result(
        state=State.OK if "online" in share["shareStatusString"].lower() else State.WARN,
        summary=share["shareStatusString"],
    )
    yield Result(state=State.OK, summary=f"Access Protocol: {share.get('accessProtocolString')}")

    if share.get("deduplicationEnabled", False):
        yield Result(state=State.OK, summary=f"Dedup ratio: {share.get('dedupeRatio', 0):0.1f}")

    if share.get("description"):
        yield Result(state=State.OK, summary="Description: " + share.get("description"))

    yield Result(state=State.OK, summary=f"Path: {share.get('networkPath')}")
    yield Result(state=State.OK, notice=f"Created Date: {share.get('createdDate')}")

    yield Result(
        state=State.OK,
        notice=f"Encryption: {'Enabled' if share.get('encryptionEnabled') else 'Disabled'}",
    )
    yield Result(state=State.OK, notice=f"Created Date: {share.get('createdDate')}")

    mega = 1024 * 1024
    size_available_mb = share["sizeOnDiskQuotaBytes"] / mega
    size_used_mb = share["diskBytes"] / mega
    if share.get("sizeOnDiskQuotaEnabled", False):
        yield from df_check_filesystem_list(
            value_store=get_value_store(),
            item=item,
            params=params,
            fslist_blocks=[(item, size_available_mb, size_available_mb - size_used_mb, 0)],
        )

    yield Result(state=State.OK, summary="UserBytes: %s" % render.bytes(share.get("userBytes", 0)))
    yield Metric("dedup_rate", share.get("dedupeRatio", 0))
    yield Metric("file_count", share.get("numFiles", 0))


check_plugin_storeonce4x_nas_stores = CheckPlugin(
    name="storeonce4x_nas_shares",
    service_name="NAS Share %s",
    discovery_function=discover_storeonce4x_nas_shares,
    check_function=check_storeonce4x_nas_shares,
    check_ruleset_name="filesystem",
    check_default_parameters=FILESYSTEM_DEFAULT_PARAMS,
)
