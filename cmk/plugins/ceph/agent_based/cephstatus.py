#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import json
import time
from collections.abc import Mapping, MutableMapping, Sequence
from dataclasses import dataclass
from typing import Any, Self

from cmk.agent_based.v2 import (
    AgentSection,
    check_levels,
    CheckPlugin,
    CheckResult,
    DiscoveryResult,
    get_value_store,
    HostLabel,
    HostLabelGenerator,
    Metric,
    render,
    Result,
    Service,
    State,
    StringTable,
)
from cmk.plugins.ceph.constants import MIB, PG_METRICS_MAP
from cmk.plugins.lib import df


@dataclass(frozen=True)
class HealthCheck:
    name: str
    muted: bool
    message: str
    severity: State


@dataclass(frozen=True)
class HealthSummary:
    severity: State
    message: str


@dataclass
class Health:
    overall_ok: bool
    checks: Sequence[HealthCheck]
    summaries: Sequence[HealthSummary]

    @classmethod
    def from_raw(cls, raw: Mapping[str, Any]) -> Self | None:
        if (status := raw.get("status")) is not None:
            return cls(
                overall_ok=status == "HEALTH_OK",
                checks=tuple(
                    HealthCheck(
                        name=str(check),
                        muted=bool(raw_check.get("muted")),
                        message=str(raw_check["summary"]["message"]),
                        severity=(
                            State.WARN if raw_check["severity"] == "HEALTH_WARN" else State.CRIT
                        ),
                    )
                    for check, raw_check in raw.get("checks", {}).items()
                ),
                summaries=(),
            )

        if (status := raw.get("overall_status")) is not None:
            return cls(
                overall_ok=status == "HEALTH_OK",
                checks=(),
                summaries=tuple(
                    HealthSummary(
                        severity=State.WARN if data["severity"] == "HEALTH_WARN" else State.CRIT,
                        message=str(data["summary"]),
                    )
                    for data in raw["summary"]
                ),
            )

        return None


@dataclass(frozen=True)
class OSDMap:
    full: bool
    nearfull: bool

    @classmethod
    def from_raw(cls, raw: Mapping[str, Any]) -> Self:
        return cls(full=bool(raw.get("full")), nearfull=bool(raw.get("nearfull")))


@dataclass(frozen=True)
class PGState:
    state_name: str
    count: int


@dataclass(frozen=True)
class PGMap:
    size_mb: float | None
    avail_mb: float | None
    num_objects: int | None
    num_pgs: int | None
    degraded_objects: int | None
    degraded_total: int | None
    misplaced_objects: int | None
    misplaced_total: int | None
    recovering: float | None
    pgstates: Sequence[PGState]

    @classmethod
    def from_raw(cls, raw: Mapping[str, Any]) -> Self:
        return cls(
            size_mb=None if (v := raw.get("bytes_total")) is None else float(v) / MIB,
            avail_mb=None if (v := raw.get("bytes_avail")) is None else float(v) / MIB,
            num_objects=None if (v := raw.get("num_objects")) is None else int(v),
            num_pgs=None if (v := raw.get("num_pgs")) is None else int(v),
            degraded_objects=None if (v := raw.get("degraded_objects")) is None else int(v),
            degraded_total=None if (v := raw.get("degraded_total")) is None else int(v),
            misplaced_objects=None if (v := raw.get("misplaced_objects")) is None else int(v),
            misplaced_total=None if (v := raw.get("misplaced_total")) is None else int(v),
            recovering=None if (v := raw.get("recovering_bytes_per_sec")) is None else float(v),
            pgstates=tuple(
                PGState(state_name=str(raw_pgstate["state_name"]), count=int(raw_pgstate["count"]))
                for raw_pgstate in raw["pgs_by_state"]
            ),
        )


@dataclass(frozen=True)
class Section:
    error: str | None
    health: Health | None
    osdmap: OSDMap | None
    pgmap: PGMap | None
    dashboard: str | None

    @classmethod
    def from_raw(cls, raw: Mapping[str, Any]) -> Self:
        try:
            dashboard = str(raw["mgrmap"]["services"]["dashboard"])
        except KeyError:
            dashboard = None

        return cls(
            error=None if (raw_err := raw.get("deployment_error")) is None else str(raw_err),
            health=(
                None if (raw_health := raw.get("health")) is None else Health.from_raw(raw_health)
            ),
            osdmap=(
                None
                if (raw_osdmap := raw.get("osdmap", {}).get("osdmap")) is None
                else OSDMap.from_raw(raw_osdmap)
            ),
            pgmap=None if (raw_pgmap := raw.get("pgmap")) is None else PGMap.from_raw(raw_pgmap),
            dashboard=dashboard,
        )


def parse_cephstatus(string_table: StringTable) -> Section:
    return Section.from_raw(json.loads("".join(string_table[0])))


def host_label_cephstatus(section: Section) -> HostLabelGenerator:
    """Host label function

    Labels:
        cmk/ceph/mon:
            This label is set to 'yes' in case a Ceph health status is present.
    """
    if section.health:
        yield HostLabel("cmk/ceph/mon", "yes")


agent_section_cephstatus = AgentSection(
    name="cephstatus",
    parse_function=parse_cephstatus,
    host_label_function=host_label_cephstatus,
)


def discover_cephstatus(section: Section) -> DiscoveryResult:
    if section.health or section.error:
        yield Service(item="Status")


def check_cephstatus(item: str, params: Mapping[str, object], section: Section) -> CheckResult:
    yield from check_cephstatus_testable(item, params, section, time.time(), get_value_store())


def check_cephstatus_testable(
    item: str,
    params: Mapping[str, object],
    section: Section,
    now: float,
    value_store: MutableMapping[str, Any],
) -> CheckResult:
    if section.health is not None:
        yield from _check_health(section.health)
    elif section.error is not None:
        yield Result(state=State.CRIT, summary=section.error)
    else:
        yield Result(state=State.UNKNOWN, summary="Overall health information not found")

    if section.osdmap is not None:
        yield from _check_osdmap(section.osdmap)

    if section.pgmap is not None:
        yield from _check_pgmap(section.pgmap, item, params, value_store, now)

    if section.dashboard:
        yield Result(state=State.OK, summary=f"Dashboard: {section.dashboard}")


def _check_health(health: Health) -> CheckResult:
    if health.overall_ok:
        yield Result(state=State.OK, summary="Overall health OK")
        return

    for check in health.checks:
        yield Result(
            state=State.OK if check.muted else check.severity,
            summary=f"{check.name}: {check.message}{' (muted)' if check.muted else ''}",
        )

    for summary in health.summaries:
        yield Result(state=summary.severity, summary=summary.message)

    if health.checks or health.summaries:
        return
    yield Result(
        state=State.UNKNOWN,
        summary="Overall Health status not found: %s" % health,
    )


def _check_osdmap(osdmap: OSDMap) -> CheckResult:
    if osdmap.full:
        yield Result(state=State.CRIT, summary="OSD map full")
    if osdmap.nearfull:
        yield Result(state=State.WARN, summary="OSD map near full")


def _check_pgmap(
    pgmap: PGMap,
    item: str,
    params: Mapping[str, object],
    value_store: MutableMapping[str, object],
    now: float,
) -> CheckResult:
    if pgmap.avail_mb is not None and pgmap.size_mb is not None:
        yield from df.df_check_filesystem_single(
            value_store,
            item,
            pgmap.size_mb,
            pgmap.avail_mb,
            0,
            None,
            None,
            params=params,
            this_time=now,
        )

    if pgmap.num_objects is not None:
        yield from check_levels(
            pgmap.num_objects, metric_name="num_objects", render_func=str, label="Objects"
        )

    if pgmap.num_pgs:
        yield from check_levels(
            pgmap.num_pgs, metric_name="num_pgs", render_func=str, label="Placement groups"
        )

    if pgmap.degraded_objects is not None and pgmap.degraded_total is not None:
        yield Metric(
            "degraded_objects", pgmap.degraded_objects, boundaries=(0, pgmap.degraded_total)
        )

    if pgmap.misplaced_objects is not None and pgmap.misplaced_total is not None:
        yield Metric(
            "misplaced_objects", pgmap.misplaced_objects, boundaries=(0, pgmap.misplaced_total)
        )

    if pgmap.recovering is not None:
        yield from check_levels(
            pgmap.recovering,
            metric_name="recovering",
            render_func=lambda x: f"{render.bytes(x)}/s",
            label="Recovering",
        )

    for pgstate in pgmap.pgstates:
        if not pgstate.count:
            continue
        yield Result(
            state=_make_state(pgstate.state_name),
            summary=f"PGs in {pgstate.state_name}: {pgstate.count}",
        )
        if (metric_name := PG_METRICS_MAP.get(pgstate.state_name)) is not None:
            yield Metric(metric_name, pgstate.count)


def _make_state(name: str) -> State:
    if "inconsistent" in name or "incomplete" in name or "active" not in name:
        return State.CRIT
    if "active+clean" not in name:
        return State.WARN
    if "stale" in name:
        return State.UNKNOWN
    return State.OK if name in PG_METRICS_MAP else State.UNKNOWN


def cluster_check_cephstatus(
    item: str, params: Mapping[str, object], section: Mapping[str, Section | None]
) -> CheckResult:
    # always take data from first node
    for node_section in section.values():
        if node_section is not None:
            yield from check_cephstatus(item, params, node_section)
            return


check_plugin_cephstatus = CheckPlugin(
    name="cephstatus",
    # The item will always be "Status", but we need it to subscribe to the "filesystem" ruleset.
    service_name="Ceph %s",
    sections=["cephstatus"],
    discovery_function=discover_cephstatus,
    check_function=check_cephstatus,
    check_ruleset_name="filesystem",
    check_default_parameters=df.FILESYSTEM_DEFAULT_PARAMS,
    cluster_check_function=cluster_check_cephstatus,
)
