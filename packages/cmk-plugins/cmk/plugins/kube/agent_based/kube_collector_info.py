#!/usr/bin/env python3
# Copyright (C) 2022 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


from collections.abc import Sequence
from typing import Literal, NamedTuple, TypedDict

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
from cmk.plugins.kube.kube import COLLECTOR_SERVICE_NAME
from cmk.plugins.kube.schemata.section import (
    CacheSizeInfo,
    CollectorComponentsMetadata,
    CollectorDaemons,
    CollectorHandlerLog,
    CollectorProcessingLogs,
    CollectorState,
    NodeComponent,
)

CacheSizeMode = Literal["percentage", "absolute"]


class Params(TypedDict):
    machine_metrics: int
    container_metrics_cache_size: tuple[CacheSizeMode, LevelsT[float] | LevelsT[int]]
    machine_sections_cache_size: tuple[CacheSizeMode, LevelsT[float] | LevelsT[int]]


DEFAULT_PARAMS = Params(
    machine_metrics=2,  # CRIT
    container_metrics_cache_size=("percentage", ("fixed", (80.0, 95.0))),
    machine_sections_cache_size=("percentage", ("fixed", (80.0, 95.0))),
)


# TODO: change section from info to components
def parse_collector_processing_logs(
    string_table: StringTable,
) -> CollectorProcessingLogs:
    return CollectorProcessingLogs.model_validate_json(string_table[0][0])


agent_section_kube_collector_processing_logs_v1 = AgentSection(
    name="kube_collector_processing_logs_v1",
    parsed_section_name="kube_collector_processing_logs",
    parse_function=parse_collector_processing_logs,
)


def parse_collector_metadata(string_table: StringTable) -> CollectorComponentsMetadata:
    return CollectorComponentsMetadata.model_validate_json(string_table[0][0])


agent_section_kube_collector_metadata_v1 = AgentSection(
    name="kube_collector_metadata_v1",
    parsed_section_name="kube_collector_metadata",
    parse_function=parse_collector_metadata,
)


def parse_collector_daemons(string_table: StringTable) -> CollectorDaemons:
    return CollectorDaemons.model_validate_json(string_table[0][0])


agent_section_kube_collector_daemons_v1 = AgentSection(
    name="kube_collector_daemons_v1",
    parsed_section_name="kube_collector_daemons",
    parse_function=parse_collector_daemons,
)


def discover(
    section_kube_collector_metadata: CollectorComponentsMetadata | None,
    section_kube_collector_processing_logs: CollectorProcessingLogs | None,
    section_kube_collector_daemons: CollectorDaemons | None,
) -> DiscoveryResult:
    if section_kube_collector_metadata is not None and section_kube_collector_daemons is not None:
        yield Service()


def _component_check(
    state_if_missing: State,
    component: Literal["container_metrics", "machine_sections"],
    component_log: CollectorHandlerLog | None,
) -> CheckResult:
    component_name = {
        "container_metrics": "Container Metrics",
        "machine_sections": "Machine Metrics",
    }[component]
    if component_log is None:
        return

    if component_log.status == CollectorState.OK:
        yield Result(state=State.OK, summary=f"{component_name}: OK")
        return

    component_message = f"{component_name}: {component_log.title}"
    # adding a whitespace, because for an URL the icon swallows the ')'
    detail_message = f"({component_log.detail} )" if component_log.detail else ""
    yield Result(
        state=state_if_missing,
        summary=component_message,
        details=f"{component_message}{detail_message}",
    )


def _collector_component_versions(components: Sequence[NodeComponent]) -> str:
    """Format component version strings for display."""
    formatted_components: list[str] = []
    for component in sorted(components, key=lambda c: c.collector_type.value):
        formatted_components.append(
            f"{component.collector_type.value}: Checkmk_kube_agent v{component.checkmk_kube_agent.project_version}, {component.name} {component.version}"
        )
    return "; ".join(formatted_components)


def _check_collector_daemons(collector_daemons: CollectorDaemons) -> CheckResult:
    for name, replica, is_duplicated, label in [
        (
            "container",
            collector_daemons.container,
            collector_daemons.errors.duplicate_container_collector,
            "node-collector=container-metrics",
        ),
        (
            "machine",
            collector_daemons.machine,
            collector_daemons.errors.duplicate_machine_collector,
            "node-collector=machine-sections",
        ),
    ]:
        if is_duplicated:
            yield Result(
                state=State.OK,
                summary=f"Multiple DaemonSets with label {label}",
            )
        elif replica is None:
            yield Result(
                state=State.OK,
                summary=f"No DaemonSet with label {label}",
            )
        else:
            yield Result(
                state=State.OK,
                summary=f"Nodes with {name} collectors: {replica.available}/{replica.desired}",
            )

    if (
        collector_daemons.errors.duplicate_container_collector
        or collector_daemons.errors.duplicate_machine_collector
    ):
        yield Result(
            state=State.OK,
            notice="Cannot identify node collector, if label is found on multiple DaemonSets",
        )
    if None in (collector_daemons.container, collector_daemons.machine):
        yield Result(
            state=State.OK,
            notice="Collector DaemonSets may be missing for multiple reasons: "
            "DaemonSets have not been deployed or DaemonSets have been "
            "deployed without their identification labels.",
        )


def _cache_result(
    cache: CacheSizeInfo,
    label: str,
    levels_config: LevelsT[float] | LevelsT[int],
    wants_percentage: bool,
) -> Result | None:
    """Evaluate cache size against thresholds with custom suffix formatting.

    check_levels is used for state calculation, but custom formatting is needed
    to avoid ugly output like "(warn/crit at 80/5000/95/5000)" and instead produce
    readable "(warn at 80%, crit at 95%)" for percentages or "(warn at 8000, crit at 9500)"
    for absolute values.
    """
    if cache.maxsize == 0:
        # It should never be 0, otherwise the collector probably isn't working.
        # But if it is, let's not crash.
        return Result(
            state=State.UNKNOWN,
            summary=f"{label}: Cache max size is 0, this is likely a configuration error",
        )
    percentage = cache.size * 100 / cache.maxsize
    value = percentage if wants_percentage else float(cache.size)
    for check_result in check_levels(value=value, levels_upper=levels_config, metric_name=None):
        if isinstance(check_result, Result):
            base = (
                f"{label}: {render.percent(percentage)} - {cache.size} of {cache.maxsize} entries"
            )
            if check_result.state == State.OK:
                return Result(state=State.OK, notice=base)
            match levels_config:
                case ("fixed", (int() | float() as warn, int() | float() as crit)):
                    suffix = (
                        f"(warn at {render.percent(warn)}, crit at {render.percent(crit)})"
                        if wants_percentage
                        else f"(warn at {int(warn)}, crit at {int(crit)})"
                    )
                case _:
                    suffix = ""
            return Result(state=check_result.state, notice=f"{base} {suffix}".strip())
    return None


def _cache_metric(
    cache: CacheSizeInfo,
    metric_name: str,
    levels_config: LevelsT[float] | LevelsT[int],
    wants_percentage: bool,
) -> Metric:
    """Build metric with cache size in absolute units, converting percentage levels if needed."""
    metric_levels: tuple[int, int] | None = None
    match levels_config:
        case ("fixed", (int() | float() as warn, int() | float() as crit)):
            metric_levels = (
                (
                    int((warn / 100.0) * cache.maxsize),
                    int((crit / 100.0) * cache.maxsize),
                )
                if wants_percentage
                else (int(warn), int(crit))
            )
        case _:
            metric_levels = None
    return Metric(metric_name, cache.size, levels=metric_levels, boundaries=(0, cache.maxsize))


class _ComponentCheckRow(NamedTuple):
    cache_key: Literal["container_metrics", "machine_sections"]
    logs_attr: Literal["container", "machine"]
    label: str
    log_missing_state: State


def check(
    params: Params,
    section_kube_collector_metadata: CollectorComponentsMetadata | None,
    section_kube_collector_processing_logs: CollectorProcessingLogs | None,
    section_kube_collector_daemons: CollectorDaemons | None,
) -> CheckResult:
    if section_kube_collector_metadata is None or section_kube_collector_daemons is None:
        return

    if section_kube_collector_metadata.processing_log.status == CollectorState.ERROR:
        # metadata is the connection foundation, if the metadata is not available then we should
        # not expect any metrics from the collector
        # adding a whitespace, because for an URL the icon swallows the ')'
        yield Result(
            state=State.CRIT,
            summary=f"Status: {section_kube_collector_metadata.processing_log.title} "
            f"({section_kube_collector_metadata.processing_log.detail} )",
        )
    else:
        # TODO: improve metadata model to remove assert CMK-9793
        # The combination where the metadata processing_log.status is OK but the cluster collector
        # metadata is None is not possible and is verified on the Special Agent side
        assert section_kube_collector_metadata.cluster_collector is not None
        yield Result(
            state=State.OK,
            summary=f"Cluster collector version: {section_kube_collector_metadata.cluster_collector.checkmk_kube_agent.project_version}",
        )

    yield from _check_collector_daemons(section_kube_collector_daemons)

    if section_kube_collector_metadata.processing_log.status == CollectorState.ERROR:
        return

    if section_kube_collector_metadata.cluster_collector is not None:
        cache_health = section_kube_collector_metadata.cluster_collector.cache_health

        components = [
            _ComponentCheckRow(
                "container_metrics",
                "container",
                "Container metrics cache size",
                State.CRIT,
            ),
            _ComponentCheckRow(
                "machine_sections",
                "machine",
                "Machine sections cache size",
                State(params["machine_metrics"]),
            ),
        ]
        for row in components:
            # Cache health
            if cache_health is not None:
                cache: CacheSizeInfo = getattr(cache_health, row.cache_key)
                mode, levels_config = params[f"{row.cache_key}_cache_size"]  # type: ignore[literal-required]
                wants_percentage: bool = mode == "percentage"
                if result := _cache_result(cache, row.label, levels_config, wants_percentage):
                    yield result
                yield _cache_metric(
                    cache,
                    f"kube_cluster_collector_{row.cache_key}_cache_size",
                    levels_config,
                    wants_percentage,
                )

            # "Did we query the thing successfully?" health
            if section_kube_collector_processing_logs is not None:
                yield from _component_check(
                    row.log_missing_state,
                    row.cache_key,
                    getattr(section_kube_collector_processing_logs, row.logs_attr),
                )

    if section_kube_collector_metadata.nodes:
        yield Result(
            state=State.OK,
            notice="\n".join(
                [
                    f"Node: {node.name} ({_collector_component_versions(list(node.components.values()))})"
                    for node in section_kube_collector_metadata.nodes
                ]
            ),
        )


check_plugin_kube_collector_info = CheckPlugin(
    name="kube_collector_info",
    service_name=COLLECTOR_SERVICE_NAME,
    sections=[
        "kube_collector_metadata",
        "kube_collector_processing_logs",
        "kube_collector_daemons",
    ],
    discovery_function=discover,
    check_function=check,
    check_ruleset_name="kube_collector_info",
    check_default_parameters=DEFAULT_PARAMS,
)
