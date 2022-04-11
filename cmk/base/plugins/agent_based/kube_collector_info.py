#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2022 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


import json
from typing import List, Optional, Sequence

from cmk.base.plugins.agent_based.agent_based_api.v1 import register, Result, Service, State
from cmk.base.plugins.agent_based.agent_based_api.v1.type_defs import (
    CheckResult,
    DiscoveryResult,
    StringTable,
)
from cmk.base.plugins.agent_based.utils.kube import (
    CollectorComponentsMetadata,
    CollectorHandlerLog,
    CollectorProcessingLogs,
    CollectorState,
    NodeComponent,
)


# TODO: change section from info to components
def parse_collector_processing_logs(string_table: StringTable) -> CollectorProcessingLogs:
    return CollectorProcessingLogs(**json.loads(string_table[0][0]))


register.agent_section(
    name="kube_collector_processing_logs_v1",
    parsed_section_name="kube_collector_processing_logs",
    parse_function=parse_collector_processing_logs,
)


def parse_collector_metadata(string_table: StringTable) -> CollectorComponentsMetadata:
    return CollectorComponentsMetadata(**json.loads(string_table[0][0]))


register.agent_section(
    name="kube_collectors_metadata_v1",
    parsed_section_name="kube_collectors_metadata",
    parse_function=parse_collector_metadata,
)


def discover(
    section_kube_collectors_metadata: Optional[CollectorComponentsMetadata],
    section_kube_collector_processing_logs: Optional[CollectorProcessingLogs],
) -> DiscoveryResult:
    if section_kube_collectors_metadata is not None:
        yield Service()


def _component_check(component: str, component_log: Optional[CollectorHandlerLog]):
    if component_log is None:
        return

    if component_log.status == CollectorState.OK:
        yield Result(state=State.OK, summary=f"{component}: OK")
        return

    component_message = f"{component}: {component_log.title}"
    # adding a whitespace, because for an URL the icon swallows the ')'
    detail_message = f"({component_log.detail} )" if component_log.detail else ""
    yield Result(
        state=State.OK,
        summary=component_message,
        details=f"{component_message}{detail_message}",
    )


def _collector_component_versions(components: Sequence[NodeComponent]) -> str:
    """
    Examples:
        >>> from cmk.base.plugins.agent_based.utils.kube import CollectorType, CheckmkKubeAgentMetadata
        >>> _collector_component_versions([NodeComponent(name="component", version="1",
        ... checkmk_kube_agent=CheckmkKubeAgentMetadata(project_version="1"),
        ... collector_type=CollectorType.CONTAINER_METRICS)])
        'Container Metrics: Checkmk_kube_agent v1, component 1'
    """
    formatted_components: List[str] = []
    for component in sorted(components, key=lambda c: c.collector_type.value):
        formatted_components.append(
            f"{component.collector_type.value}: Checkmk_kube_agent v{component.checkmk_kube_agent.project_version}, {component.name} {component.version}"
        )
    return "; ".join(formatted_components)


def check(
    section_kube_collectors_metadata: Optional[CollectorComponentsMetadata],
    section_kube_collector_processing_logs: Optional[CollectorProcessingLogs],
) -> CheckResult:
    if section_kube_collectors_metadata is None:
        return

    if section_kube_collectors_metadata.processing_log.status == CollectorState.ERROR:
        # metadata is the connection foundation, if the metadata is not available then we should
        # not expect any metrics from the collector
        # adding a whitespace, because for an URL the icon swallows the ')'
        yield Result(
            state=State.CRIT,
            summary=f"Status: {section_kube_collectors_metadata.processing_log.title} "
            f"({section_kube_collectors_metadata.processing_log.detail} )",
        )
        return

    # TODO: improve metadata model to remove assert CMK-9793
    # The combination where the metadata processing_log.status is OK but the cluster collector
    # metadata is None is not possible and is verified on the Special Agent side
    assert section_kube_collectors_metadata.cluster_collector is not None

    yield Result(
        state=State.OK,
        summary=f"Cluster collector version: {section_kube_collectors_metadata.cluster_collector.checkmk_kube_agent.project_version}",
    )

    yield Result(
        state=State.OK,
        summary=f"Nodes with collectors: {len(section_kube_collectors_metadata.nodes) if section_kube_collectors_metadata.nodes else 0}",
    )

    if section_kube_collector_processing_logs is not None:
        yield from _component_check(
            "Container Metrics", section_kube_collector_processing_logs.container
        )
        yield from _component_check(
            "Machine Metrics", section_kube_collector_processing_logs.machine
        )

    if section_kube_collectors_metadata.nodes:
        yield Result(
            state=State.OK,
            notice="\n".join(
                [
                    f"Node: {node.name} ({_collector_component_versions(list(node.components.values()))})"
                    for node in section_kube_collectors_metadata.nodes
                ]
            ),
        )


register.check_plugin(
    name="kube_collector_info",
    service_name="Cluster Collector",
    sections=["kube_collectors_metadata", "kube_collector_processing_logs"],
    discovery_function=discover,
    check_function=check,
)
