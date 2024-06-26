#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import json
import time
from collections.abc import Mapping, MutableMapping
from dataclasses import dataclass
from typing import Any

from cmk.agent_based.v2 import (
    AgentSection,
    check_levels,
    CheckPlugin,
    CheckResult,
    DiscoveryResult,
    get_value_store,
    HostLabel,
    HostLabelGenerator,
    Result,
    Service,
    ServiceLabel,
    State,
    StringTable,
)
from cmk.plugins.lib import df


@dataclass(frozen=True)
class OSD:
    id: int
    device_class: str | None
    size_mb: float
    avail_mb: float
    pgs: int | None
    status: str | None


@dataclass(frozen=True)
class LatencyStats:
    apply: int
    commit: int


@dataclass(frozen=True)
class Section:
    df_nodes: Mapping[str, OSD]
    osd_perf: Mapping[str, LatencyStats]


_KIB = 1024.0


def parse_cephosd(string_table: StringTable) -> Section | None:
    raw_section = json.loads("".join(string_table[0]))

    try:
        return Section(
            df_nodes={
                str(raw["id"]): OSD(
                    id=raw["id"],
                    device_class=None if (dc := raw.get("device_class")) is None else str(dc),
                    size_mb=float(raw["kb"]) / _KIB,
                    avail_mb=float(raw["kb_avail"]) / _KIB,
                    pgs=None if (pgs := raw.get("pgs")) is None else int(pgs),
                    status=None if (status := raw.get("status")) is None else str(status),
                )
                for raw in raw_section.get("df", {}).get("nodes", ())
            },
            osd_perf={
                str(raw["id"]): LatencyStats(
                    apply=raw["perf_stats"]["apply_latency_ms"],
                    commit=raw["perf_stats"]["commit_latency_ms"],
                )
                for raw in raw_section.get("perf", {}).get("osd_perf_infos", ())
            },
        )
    except KeyError:
        return None


def host_label_cephosd(section: Section) -> HostLabelGenerator:
    """Host label function

    Labels:
        cmk/ceph/osd:
            This label is set to 'yes' in case a Ceph Object Storage Daemon is present.
    """
    if section.df_nodes:
        yield HostLabel("cmk/ceph/osd", "yes")


agent_section_cephosd = AgentSection(
    name="cephosd",
    parse_function=parse_cephosd,
    host_label_function=host_label_cephosd,
)


def discover_cephosd(section: Section) -> DiscoveryResult:
    yield from (
        Service(
            item=item,
            labels=(
                [ServiceLabel("cephosd/device_class", osd.device_class)] if osd.device_class else []
            ),
        )
        for item, osd in section.df_nodes.items()
    )


def _render_ms(seconds: float) -> str:
    return f"{seconds * 1000.0:.0f}ms"


def check_cephosd(item: str, params: Mapping[str, object], section: Section) -> CheckResult:
    yield from check_cephosd_testable(item, params, section, get_value_store(), time.time())


def check_cephosd_testable(
    item: str,
    params: Mapping[str, object],
    section: Section,
    value_store: MutableMapping[str, Any],
    now: float,
) -> CheckResult:
    if (osd := section.df_nodes.get(item)) is None:
        return

    yield from df.df_check_filesystem_single(
        value_store, item, osd.size_mb, osd.avail_mb, 0, None, None, params=params, this_time=now
    )
    if osd.pgs is not None:
        yield from check_levels(osd.pgs, metric_name="num_pgs", render_func=str, label="PGs")

    if osd.status:
        yield Result(
            state=State.OK if osd.status == "up" else State.WARN, notice=f"Status: {osd.status}"
        )

    if (osd_latency := section.osd_perf.get(item)) is None:
        return

    yield from check_levels(
        osd_latency.apply / 1000.0,
        metric_name="apply_latency",
        render_func=_render_ms,
        label="Apply latency",
    )
    yield from check_levels(
        osd_latency.commit / 1000.0,
        metric_name="commit_latency",
        render_func=_render_ms,
        label="Commit latency",
    )


check_plugin_cephosd = CheckPlugin(
    name="cephosd",
    service_name="Ceph OSD %s",
    discovery_function=discover_cephosd,
    check_function=check_cephosd,
    check_default_parameters=df.FILESYSTEM_DEFAULT_PARAMS,
    check_ruleset_name="filesystem",
)
