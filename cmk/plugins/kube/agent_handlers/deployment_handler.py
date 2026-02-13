#!/usr/bin/env python3
# Copyright (C) 2023 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
from __future__ import annotations

from collections.abc import Iterator

from cmk.plugins.kube.agent_handlers.common import (
    AnnotationOption,
    CheckmkHostSettings,
    controller_spec,
    controller_strategy,
    Deployment,
    filter_annotations_by_key_pattern,
    thin_containers,
)
from cmk.plugins.kube.common import SectionName, WriteableSection
from cmk.plugins.kube.schemata import api, section

# TODO: addition of test framework for output sections


def create_api_sections(
    api_deployment: Deployment, host_settings: CheckmkHostSettings, piggyback_name: str
) -> Iterator[WriteableSection]:
    yield from (
        WriteableSection(
            piggyback_name=piggyback_name,
            section_name=SectionName("kube_deployment_info_v1"),
            section=_info(
                api_deployment,
                host_settings.cluster_name,
                host_settings.kubernetes_cluster_hostname,
                host_settings.annotation_key_pattern,
            ),
        ),
        WriteableSection(
            piggyback_name=piggyback_name,
            section_name=SectionName("kube_pod_resources_v1"),
            section=api_deployment.pod_resources(),
        ),
        WriteableSection(
            piggyback_name=piggyback_name,
            section_name=SectionName("kube_memory_resources_v1"),
            section=api_deployment.memory_resources(),
        ),
        WriteableSection(
            piggyback_name=piggyback_name,
            section_name=SectionName("kube_cpu_resources_v1"),
            section=api_deployment.cpu_resources(),
        ),
        WriteableSection(
            piggyback_name=piggyback_name,
            section_name=SectionName("kube_update_strategy_v1"),
            section=controller_strategy(api_deployment),
        ),
        WriteableSection(
            piggyback_name=piggyback_name,
            section_name=SectionName("kube_controller_spec_v1"),
            section=controller_spec(api_deployment),
        ),
        WriteableSection(
            piggyback_name=piggyback_name,
            section_name=SectionName("kube_deployment_replicas_v1"),
            section=_replicas(api_deployment),
        ),
    )

    if (section_conditions := _conditions(api_deployment.status)) is not None:
        yield WriteableSection(
            piggyback_name=piggyback_name,
            section_name=SectionName("kube_deployment_conditions_v1"),
            section=section_conditions,
        )


def _replicas(deployment: Deployment) -> section.DeploymentReplicas:
    return section.DeploymentReplicas(
        available=deployment.status.replicas.available,
        desired=deployment.status.replicas.replicas,
        ready=deployment.status.replicas.ready,
        updated=deployment.status.replicas.updated,
    )


def _info(
    deployment: Deployment,
    cluster_name: str,
    kubernetes_cluster_hostname: str,
    annotation_key_pattern: AnnotationOption,
) -> section.DeploymentInfo:
    return section.DeploymentInfo(
        name=deployment.metadata.name,
        namespace=deployment.metadata.namespace,
        creation_timestamp=deployment.metadata.creation_timestamp,
        labels=deployment.metadata.labels,
        annotations=filter_annotations_by_key_pattern(
            deployment.metadata.annotations, annotation_key_pattern
        ),
        selector=deployment.spec.selector,
        containers=thin_containers(deployment.pods),
        cluster=cluster_name,
        kubernetes_cluster_hostname=kubernetes_cluster_hostname,
    )


def _conditions(
    deployment_status: api.DeploymentStatus,
) -> section.DeploymentConditions | None:
    if not deployment_status.conditions:
        return None
    return section.DeploymentConditions(**deployment_status.conditions)
