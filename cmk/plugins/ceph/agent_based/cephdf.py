#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import json
import time
from collections.abc import Mapping, MutableMapping
from dataclasses import dataclass
from typing import Any, Self

from cmk.agent_based.v2 import (
    AgentSection,
    check_levels,
    CheckPlugin,
    CheckResult,
    DiscoveryResult,
    get_rate,
    get_value_store,
    render,
    Service,
    StringTable,
)
from cmk.plugins.ceph.constants import MIB
from cmk.plugins.lib import df

Stats = Mapping[str, int]


@dataclass(frozen=True)
class Pool:
    id: int
    name: str
    stats: Stats


@dataclass(frozen=True)
class Section:
    pools: Mapping[str, Pool]
    stats_by_class: Mapping[str, Stats]


def parse_cephdf(string_table: StringTable) -> Section | None:
    raw_section = json.loads("".join(string_table[0]))

    try:
        return Section(
            pools={
                str(p["name"]): Pool(
                    id=int(p["id"]),
                    name=str(p["name"]),
                    stats={str(k): int(v) for k, v in p["stats"].items()},
                )
                for p in raw_section["pools"]
            },
            stats_by_class={
                str(c): {str(k): int(v) for k, v in raw_stats.items()}
                for c, raw_stats in raw_section["stats_by_class"].items()
            },
        )
    except KeyError:
        return None


agent_section_cephdf = AgentSection(
    name="cephdf",
    parse_function=parse_cephdf,
)


def discover_cephdf(section: Section) -> DiscoveryResult:
    yield from (Service(item=pool_name) for pool_name in section.pools)


def check_cephdf(item: str, params: Mapping[str, object], section: Section) -> CheckResult:
    yield from check_cephdf_testable(item, params, section, time.time(), get_value_store())


@dataclass(frozen=True)
class Usage:
    used_mb: float
    avail_mb: float
    size_mb: float

    @classmethod
    def from_stats(cls, stats: Stats) -> Self:
        if "stored" in stats:
            # netto
            used_mb = stats["stored"] / MIB
            if (max_avail := stats.get("max_avail")) is not None and max_avail > 0:
                return cls(
                    used_mb=used_mb,
                    avail_mb=(avail_mb := max_avail / MIB),
                    size_mb=avail_mb + used_mb,
                )

            if (perc_used := stats.get("percent_used")) is not None:
                size_mb = used_mb / perc_used
                return cls(
                    used_mb=used_mb,
                    size_mb=size_mb,
                    avail_mb=size_mb - used_mb,
                )

            return cls(used_mb=used_mb, avail_mb=0.0, size_mb=0.0)

        # brutto
        used_mb = stats["bytes_used"] / MIB
        if (perc_used := stats.get("percent_used")) is not None:
            return cls(
                used_mb=used_mb,
                size_mb=(size_mb := used_mb / perc_used),
                avail_mb=size_mb - used_mb,
            )
        return cls(used_mb=used_mb, avail_mb=0.0, size_mb=0.0)


def check_cephdf_testable(
    item: str,
    params: Mapping[str, object],
    section: Section,
    now: float,
    value_store: MutableMapping[str, Any],
) -> CheckResult:
    if (pool := section.pools.get(item)) is None:
        return

    usage = Usage.from_stats(pool.stats)

    yield from df.df_check_filesystem_single(
        value_store,
        item,
        usage.size_mb,
        usage.avail_mb,
        0,
        None,
        None,
        params=params,
        this_time=now,
    )

    yield from check_levels(pool.stats["objects"], metric_name="num_objects", label="Objects")

    yield from check_levels(
        get_rate(value_store, "%s.ri" % item, now, pool.stats["rd"]),
        metric_name="disk_read_ios",
        label="Read IOPS",
    )
    yield from check_levels(
        get_rate(value_store, "%s.wi" % item, now, pool.stats["wr"]),
        metric_name="disk_write_ios",
        label="Write IOPS",
    )
    yield from check_levels(
        get_rate(value_store, "%s.rb" % item, now, pool.stats["rd_bytes"]),
        metric_name="disk_read_throughput",
        render_func=render.bytes,
        label="Read Throughput",
    )
    yield from check_levels(
        get_rate(value_store, "%s.wb" % item, now, pool.stats["wr_bytes"]),
        metric_name="disk_write_throughput",
        render_func=render.bytes,
        label="Write Throughput",
    )


def cluster_check_cephdf(
    item: str, params: Mapping[str, object], section: Mapping[str, Section | None]
) -> CheckResult:
    # always take data from first node
    for node_section in section.values():
        if node_section is not None:
            yield from check_cephdf(item, params, node_section)
            return


check_plugin_cephdf = CheckPlugin(
    name="cephdf",
    service_name="Ceph Pool %s",
    discovery_function=discover_cephdf,
    check_function=check_cephdf,
    check_ruleset_name="filesystem",
    check_default_parameters=df.FILESYSTEM_DEFAULT_PARAMS,
    cluster_check_function=cluster_check_cephdf,
)


def discovery_cephdfclass(section: Section) -> DiscoveryResult:
    for cls in section.stats_by_class:
        yield Service(item=cls)


def check_cephdfclass(item: str, params: Mapping[str, object], section: Section) -> CheckResult:
    yield from check_cephdfclass_testable(item, params, section, time.time(), get_value_store())


def check_cephdfclass_testable(
    item: str,
    params: Mapping[str, object],
    section: Section,
    now: float,
    value_store: MutableMapping[str, Any],
) -> CheckResult:
    if (stats := section.stats_by_class.get(item)) is None:
        return

    avail_mb = stats["total_avail_bytes"] / MIB
    size_mb = stats["total_bytes"] / MIB

    yield from df.df_check_filesystem_single(
        value_store, item, size_mb, avail_mb, 0, None, None, params=params, this_time=now
    )


def cluster_check_cephdfclass(
    item: str, params: Mapping[str, object], section: Mapping[str, Section | None]
) -> CheckResult:
    # always take data from first node
    for node_section in section.values():
        if node_section is not None:
            yield from check_cephdfclass(item, params, node_section)


check_plugin_cephdfclass = CheckPlugin(
    name="cephdfclass",
    service_name="Ceph Class %s",
    sections=["cephdf"],
    discovery_function=discovery_cephdfclass,
    check_function=check_cephdfclass,
    check_ruleset_name="filesystem",
    check_default_parameters=df.FILESYSTEM_DEFAULT_PARAMS,
    cluster_check_function=cluster_check_cephdfclass,
)
