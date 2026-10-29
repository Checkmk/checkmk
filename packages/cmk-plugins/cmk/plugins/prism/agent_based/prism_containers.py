#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
# ported by (c) Andreas Doehler <andreas.doehler@bechtle.com/andreas.doehler@gmail.com>

# mypy: disable-error-code="explicit-any"

from collections.abc import Mapping, Sequence
from contextlib import suppress
from typing import Any

from cmk.agent_based.v2 import (
    AgentSection,
    CheckPlugin,
    CheckResult,
    DiscoveryResult,
    get_value_store,
    GetRateError,
    Metric,
    Result,
    Service,
    State,
    StringTable,
)
from cmk.plugins.lib.df import df_check_filesystem_single, FILESYSTEM_DEFAULT_PARAMS
from cmk.plugins.prism.lib import load_json
from cmk.plugins.prism.v4_models import (
    Sample,
    StorageContainerStats,
    StorageContainersWithStats,
)

Section = Mapping[str, Mapping[str, Any]]


def parse_prism_container(string_table: StringTable) -> Section:
    parsed: dict[str, dict[str, Any]] = {}
    data = load_json(string_table)
    for element in data.get("entities", {}):
        parsed.setdefault(element.get("name", "unknown"), element)
    return parsed


agent_section_prism_containers = AgentSection(
    name="prism_containers",
    parse_function=parse_prism_container,
)


def _newest(samples: Sequence[Sample]) -> int | None:
    return max(samples, key=lambda sample: sample.timestamp).value if samples else None


def _usage_stats_v2(stats: StorageContainerStats) -> dict[str, str]:
    # v4 counts every replica, the legacy API only what is usable
    replication_factor = _newest(stats.storage_replication_factor)
    dedup = _newest(stats.data_reduction_dedup_saving_ratio_ppm)
    # -1 is how the legacy API reports an unknown ratio, the check then leaves it out
    usage_stats = {"data_reduction.dedup.saving_ratio_ppm": str(-1 if dedup is None else dedup)}
    for legacy_key, samples in (
        ("storage.user_capacity_bytes", stats.storage_capacity_bytes),
        ("storage.user_free_bytes", stats.storage_free_bytes),
    ):
        if (value := _newest(samples)) is not None and replication_factor:
            usage_stats[legacy_key] = str(value // replication_factor)
    return usage_stats


def parse_prism_containers_v2(string_table: StringTable) -> Section:
    if not string_table:
        return {}
    # Nutanix keeps container names unique within a cluster, and each cluster has its own host
    return {
        container.name: {
            "usageStats": _usage_stats_v2(container.stats),
            "fingerPrintOnWrite": "on" if container.cache_deduplication == "ON" else "off",
        }
        for container in StorageContainersWithStats.model_validate_json(string_table[0][0]).root
    }


agent_section_prism_containers_v2 = AgentSection(
    name="prism_containers_v2",
    parsed_section_name="prism_containers",
    parse_function=parse_prism_containers_v2,
)


def discovery_prism_container(section: Section) -> DiscoveryResult:
    for item in section:
        yield Service(item=item)


def check_prism_container(item: str, params: Mapping[str, Any], section: Section) -> CheckResult:
    value_store = get_value_store()
    data = section.get(item)
    if not data:
        return

    capacity, freebytes, dedupratio = map(
        int,
        (
            data["usageStats"].get("storage.user_capacity_bytes", 0),
            data["usageStats"].get("storage.user_free_bytes", 0),
            data["usageStats"].get("data_reduction.dedup.saving_ratio_ppm", 0),
        ),
    )

    with suppress(GetRateError):
        yield from df_check_filesystem_single(
            value_store,
            item,
            capacity / 1024**2,
            freebytes / 1024**2,
            0,
            None,
            None,
            params=params,
        )

    if data.get("fingerPrintOnWrite") == "on" and dedupratio != -1:
        dedup_rate = float(dedupratio) / 1000000.0
        summary = f"Dedup Ratio: {dedup_rate:.2f}"
        yield Metric("dedup_ratio", dedup_rate)
        yield Result(state=State.OK, summary=summary)


check_plugin_prism_containers = CheckPlugin(
    name="prism_containers",
    service_name="NTNX Container %s",
    sections=["prism_containers"],
    check_default_parameters=FILESYSTEM_DEFAULT_PARAMS,
    discovery_function=discovery_prism_container,
    check_function=check_prism_container,
    check_ruleset_name="filesystem",
)
