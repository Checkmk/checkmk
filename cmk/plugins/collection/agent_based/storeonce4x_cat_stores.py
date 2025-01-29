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


def parse_storeonce4x_cat_stores(string_table: StringTable) -> Section:
    return {
        "%d - %s" % (elem["id"], elem["name"]): elem  #
        for elem in json.loads(string_table[0][0])["members"]
    }


agent_section_storeonce4x_cat_stores = AgentSection(
    name="storeonce4x_cat_stores",
    parse_function=parse_storeonce4x_cat_stores,
)


def discover_storeonce4x_cat_stores(section: Section) -> DiscoveryResult:
    yield from (Service(item=k) for k in section)


def check_storeonce4x_cat_stores(
    item: str,
    params: Mapping[str, Any],
    section: Section,
) -> CheckResult:
    if (store := section.get(item)) is None:
        return

    mega = 1024 * 1024
    store_status, store_status_str = store["storeStatus"], store["storeStatusString"]
    dedup_ratio = store["dedupeRatio"]
    size_available_mb = store["sizeOnDiskQuotaBytes"] / mega
    size_used_mb = store["diskBytes"] / mega
    user_bytes = store["userBytes"]
    num_items = store["numItems"]

    if store.get("sizeOnDiskQuotaEnabled", False):
        yield from df_check_filesystem_list(
            value_store=get_value_store(),
            item=item,
            params=params,
            fslist_blocks=[(item, size_available_mb, size_available_mb - size_used_mb, 0)],
        )

    yield Result(
        state=State.OK if store_status == 2 else State.CRIT,
        summary="Status: %s" % store_status_str,
    )

    yield Result(state=State.OK, summary="Description: %s" % store["description"])
    yield Result(state=State.OK, summary="UserBytes: %s" % render.bytes(user_bytes))
    yield Result(state=State.OK, summary="Dedup ratio: %.2f" % dedup_ratio)
    yield Metric("dedup_rate", dedup_ratio)
    yield Result(state=State.OK, summary="Files: %d" % num_items)
    yield Metric("file_count", num_items)


check_plugin_storeonce4x_cat_stores = CheckPlugin(
    name="storeonce4x_cat_stores",
    service_name="Catalyst Stores %s",
    discovery_function=discover_storeonce4x_cat_stores,
    check_function=check_storeonce4x_cat_stores,
    check_ruleset_name="filesystem",
    check_default_parameters=FILESYSTEM_DEFAULT_PARAMS,
)
