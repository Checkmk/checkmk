#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Mapping, Sequence
from typing import Literal, TypedDict

from pydantic import BaseModel, NonNegativeFloat, NonNegativeInt

from cmk.agent_based.v2 import (
    AgentSection,
    check_levels,
    CheckPlugin,
    CheckResult,
    DiscoveryResult,
    LevelsT,
    Metric,
    render,
    Result,
    Service,
    State,
    StringTable,
)

Payload = Literal["kubelet_stats", "kubelet_health", "system_agent"]
PAYLOAD_LABELS: Mapping[Payload, str] = {
    "kubelet_stats": "Kubelet statistics",
    "kubelet_health": "Kubelet health",
    "system_agent": "System agent",
}


class IngestionHealth(BaseModel):
    last_heard_age_secs: NonNegativeFloat | None
    scrape_time_secs: NonNegativeFloat | None
    version: str | None
    git_sha: str | None


class NodeHealth(BaseModel):
    kubelet_stats: IngestionHealth
    kubelet_health: IngestionHealth
    system_agent: IngestionHealth


class ReflectorHealth(BaseModel):
    has_been_initialized: bool
    relist_started_age_secs: NonNegativeFloat | None
    relist_completed_age_secs: NonNegativeFloat | None
    relist_duration_secs: NonNegativeFloat | None
    last_error_age_secs: NonNegativeFloat | None
    errors_total: NonNegativeInt
    last_event_age_secs: NonNegativeFloat | None


class ClusterAggregatorMetadata(BaseModel):
    version: str
    git_sha: str | None


class AgentHealth(BaseModel):
    node_scrapers: dict[str, NodeHealth]
    reflector_healths: dict[str, ReflectorHealth]
    cluster_aggregator: ClusterAggregatorMetadata


class ScraperParams(TypedDict):
    age: LevelsT[float]
    missing_state: int
    version_state: int


class ReflectorParams(TypedDict):
    uninitialized_state: int
    relist_age: LevelsT[float]
    recent_error_window: tuple[Literal["disabled"], None] | tuple[Literal["enabled"], float]
    recent_error_state: int
    last_event_age: LevelsT[float]


class HealthParams(TypedDict):
    scrapers: ScraperParams
    reflectors: ReflectorParams
    empty_scrapers_state: int
    empty_reflectors_state: int


class DiscoveryParams(TypedDict):
    nodes: bool
    reflectors: bool


DEFAULT_SCRAPER_PARAMS = ScraperParams(
    age=("fixed", (90.0, 120.0)),
    missing_state=2,
    version_state=0,
)
DEFAULT_REFLECTOR_PARAMS = ReflectorParams(
    uninitialized_state=1,
    relist_age=("fixed", (120.0, 300.0)),
    recent_error_window=("disabled", None),
    recent_error_state=1,
    last_event_age=("no_levels", None),
)
DEFAULT_PARAMS = HealthParams(
    scrapers=DEFAULT_SCRAPER_PARAMS,
    reflectors=DEFAULT_REFLECTOR_PARAMS,
    empty_scrapers_state=1,
    empty_reflectors_state=2,
)
DEFAULT_DISCOVERY_PARAMS = DiscoveryParams(nodes=False, reflectors=True)


def parse_kube_agent_health(string_table: StringTable) -> AgentHealth | None:
    if not string_table:
        return None
    return AgentHealth.model_validate_json(string_table[0][0])


agent_section_kube_agent_health_v1 = AgentSection(
    name="kube_agent_health_v1",
    parsed_section_name="kube_agent_health",
    parse_function=parse_kube_agent_health,
)


def discover_kube_agent_health(section: AgentHealth) -> DiscoveryResult:  # noqa: ARG001
    yield Service()


def discover_kube_agent_health_node(
    params: DiscoveryParams, section: AgentHealth
) -> DiscoveryResult:
    if params["nodes"]:
        yield from (Service(item=node) for node in sorted(section.node_scrapers))


def discover_kube_agent_health_reflector(
    params: DiscoveryParams, section: AgentHealth
) -> DiscoveryResult:
    if params["reflectors"]:
        yield from (Service(item=kind) for kind in sorted(section.reflector_healths))


def _check_node(params: ScraperParams, node: NodeHealth, aggregator_version: str) -> CheckResult:
    params = {**DEFAULT_SCRAPER_PARAMS, **params}
    for payload in PAYLOAD_LABELS:
        health: IngestionHealth = getattr(node, payload)
        label = PAYLOAD_LABELS[payload]
        if health.last_heard_age_secs is None:
            yield Result(
                state=State(params["missing_state"]),
                summary=f"{label}: No cached data",
                details=f"{label}: No cached data (never received or expired)",
            )
            continue
        yield from check_levels(
            health.last_heard_age_secs,
            levels_upper=params["age"],
            metric_name=f"kube_agent_{payload}_age",
            label=f"{label} last received",
            render_func=lambda value: f"{render.timespan(value)} ago",
        )
        if health.scrape_time_secs is not None:
            yield from check_levels(
                health.scrape_time_secs,
                levels_upper=("no_levels", None),
                metric_name=f"kube_agent_{payload}_scrape_time",
                label=f"{label} scrape time",
                render_func=render.timespan,
                notice_only=True,
            )
        yield Result(
            state=State(params["version_state"])
            if health.version is not None and health.version != aggregator_version
            else State.OK,
            notice=f"{label} version: {health.version or 'Not reported'} "
            f"(cluster-aggregator: {aggregator_version}), Git revision: {health.git_sha or 'Not reported'}",
        )


def _check_reflector(params: ReflectorParams, health: ReflectorHealth) -> CheckResult:
    params = {**DEFAULT_REFLECTOR_PARAMS, **params}
    yield Result(
        state=State.OK if health.has_been_initialized else State(params["uninitialized_state"]),
        summary=(
            "Initial resource list loaded"
            if health.has_been_initialized
            else "Loading initial resource list"
        ),
    )
    # The producer clears the start age on completion. A completed list may be
    # arbitrarily old while the watch continues to deliver updates normally.
    if health.relist_started_age_secs is not None:
        yield from check_levels(
            health.relist_started_age_secs,
            levels_upper=params["relist_age"],
            metric_name="kube_agent_relist_age",
            label="Listing in progress for",
            render_func=render.timespan,
        )
    if health.last_error_age_secs is not None:
        mode, window = params["recent_error_window"]
        yield Result(
            state=(
                State(params["recent_error_state"])
                if mode == "enabled" and window is not None and health.last_error_age_secs < window
                else State.OK
            ),
            notice=f"Last watch error: {render.timespan(health.last_error_age_secs)} ago",
        )
    yield from check_levels(
        health.errors_total,
        metric_name="kube_agent_watch_errors",
        render_func=lambda x: str(int(x)),
        label="Watch errors since cluster-aggregator start",
        notice_only=True,
    )

    if health.relist_completed_age_secs is not None:
        summary = (
            f"Last full list completed {render.timespan(health.relist_completed_age_secs)} ago"
        )
        if health.relist_duration_secs is not None:
            summary += f" and took {render.timespan(health.relist_duration_secs)}"
            yield Metric("kube_agent_relist_duration", health.relist_duration_secs)
        yield Result(state=State.OK, notice=summary)

    if health.last_event_age_secs is None:
        yield Result(state=State.OK, summary="No resource events received")
    else:
        yield from check_levels(
            health.last_event_age_secs,
            levels_upper=params["last_event_age"],
            metric_name="kube_agent_last_event_age",
            label="Last resource event received",
            render_func=lambda value: f"{render.timespan(value)} ago",
        )


def _group_result(label: str, components: Mapping[str, Sequence[Result]]) -> Result:
    problems = sorted(
        (
            (name, result)
            for name, results in components.items()
            for result in results
            if result.state != State.OK
        ),
        key=lambda problem: (State.CRIT, State.UNKNOWN, State.WARN).index(problem[1].state),
    )
    affected = len({name for name, _result in problems})
    summary = f"{label}: {len(components) - affected}/{len(components)} healthy"
    if not problems:
        return Result(state=State.OK, summary=summary)

    details = [f"{summary}, {len(problems)} problems"]
    details.extend(
        f"{name} [{result.state.name}]: {result.details or result.summary}"
        for name, result in problems[:20]
    )
    if len(problems) > 20:
        details.append(f"{len(problems) - 20} additional problems not shown.")
        details.append(
            "Use reflector services or enable node services with the Kubernetes agent health service "
            "discovery rule for individual component diagnostics."
        )

    summary += "; " + "; ".join(
        f"{name}: {result.summary or result.details}" for name, result in problems[:3]
    )
    if len(problems) > 3:
        summary += f"; {len(problems) - 3} more problems (see details)"
    return Result(
        state=State.worst(*(result.state for _, result in problems)),
        summary=summary,
        details="\n".join(details),
    )


def check_kube_agent_health(params: HealthParams, section: AgentHealth) -> CheckResult:
    yield Result(
        state=State.OK,
        summary=f"Cluster aggregator version: {section.cluster_aggregator.version}",
        details=f"Cluster aggregator version: {section.cluster_aggregator.version}, "
        f"Git revision: {section.cluster_aggregator.git_sha or 'Not reported'}",
    )
    nodes = {
        name: [
            result
            for result in _check_node(params["scrapers"], node, section.cluster_aggregator.version)
            if isinstance(result, Result)
        ]
        for name, node in sorted(section.node_scrapers.items())
    }
    reflectors = {
        name: [
            result
            for result in _check_reflector(params["reflectors"], health)
            if isinstance(result, Result)
        ]
        for name, health in sorted(section.reflector_healths.items())
    }
    for label, components, empty_state, metric in (
        ("Node scrapers", nodes, params["empty_scrapers_state"], "scrapers"),
        ("Reflectors", reflectors, params["empty_reflectors_state"], "reflectors"),
    ):
        if components:
            yield _group_result(label, components)
        else:
            yield Result(state=State(empty_state), summary=f"{label}: None reported")
        yield Metric(f"kube_agent_{metric}", len(components))
        yield Metric(
            f"kube_agent_{metric}_affected",
            sum(
                any(result.state != State.OK for result in results)
                for results in components.values()
            ),
        )


def check_kube_agent_health_node(
    item: str, params: ScraperParams, section: AgentHealth
) -> CheckResult:
    if (node := section.node_scrapers.get(item)) is None:
        return
    yield from _check_node(params, node, section.cluster_aggregator.version)


def check_kube_agent_health_reflector(
    item: str, params: ReflectorParams, section: AgentHealth
) -> CheckResult:
    if (health := section.reflector_healths.get(item)) is None:
        return
    yield from _check_reflector(params, health)


check_plugin_kube_agent_health = CheckPlugin(
    name="kube_agent_health",
    service_name="Kubernetes agent health",
    discovery_function=discover_kube_agent_health,
    check_function=check_kube_agent_health,
    check_ruleset_name="kube_agent_health",
    check_default_parameters=DEFAULT_PARAMS,
)

check_plugin_kube_agent_health_node = CheckPlugin(
    name="kube_agent_health_node",
    service_name="Kubernetes agent node %s",
    sections=["kube_agent_health"],
    discovery_function=discover_kube_agent_health_node,
    discovery_ruleset_name="discovery_kube_agent_health",
    discovery_default_parameters=DEFAULT_DISCOVERY_PARAMS,
    check_function=check_kube_agent_health_node,
    check_ruleset_name="kube_agent_health_node",
    check_default_parameters=DEFAULT_SCRAPER_PARAMS,
)

check_plugin_kube_agent_health_reflector = CheckPlugin(
    name="kube_agent_health_reflector",
    service_name="Kubernetes agent reflector %s",
    sections=["kube_agent_health"],
    discovery_function=discover_kube_agent_health_reflector,
    discovery_ruleset_name="discovery_kube_agent_health",
    discovery_default_parameters=DEFAULT_DISCOVERY_PARAMS,
    check_function=check_kube_agent_health_reflector,
    check_ruleset_name="kube_agent_health_reflector",
    check_default_parameters=DEFAULT_REFLECTOR_PARAMS,
)
