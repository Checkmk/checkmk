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
    filter_annotations_by_key_pattern,
    StatefulSet,
    thin_containers,
)
from cmk.plugins.kube.common import SectionName, WriteableSection
from cmk.plugins.kube.schemata import section


def create_api_sections(
    api_statefulset: StatefulSet,
    host_settings: CheckmkHostSettings,
    piggyback_name: str,
) -> Iterator[WriteableSection]:
    yield from (
        WriteableSection(
            piggyback_name=piggyback_name,
            section_name=SectionName("kube_pod_resources_v1"),
            section=api_statefulset.pod_resources(),
        ),
        WriteableSection(
            piggyback_name=piggyback_name,
            section_name=SectionName("kube_memory_resources_v1"),
            section=api_statefulset.memory_resources(),
        ),
        WriteableSection(
            piggyback_name=piggyback_name,
            section_name=SectionName("kube_cpu_resources_v1"),
            section=api_statefulset.cpu_resources(),
        ),
        WriteableSection(
            piggyback_name=piggyback_name,
            section_name=SectionName("kube_statefulset_info_v1"),
            section=_info(
                api_statefulset,
                host_settings.cluster_name,
                host_settings.kubernetes_cluster_hostname,
                host_settings.annotation_key_pattern,
            ),
        ),
        WriteableSection(
            piggyback_name=piggyback_name,
            section_name=SectionName("kube_update_strategy_v1"),
            section=controller_strategy(api_statefulset),
        ),
        WriteableSection(
            piggyback_name=piggyback_name,
            section_name=SectionName("kube_controller_spec_v1"),
            section=controller_spec(api_statefulset),
        ),
        WriteableSection(
            piggyback_name=piggyback_name,
            section_name=SectionName("kube_statefulset_replicas_v1"),
            section=_replicas(api_statefulset),
        ),
    )


def _replicas(statefulset: StatefulSet) -> section.StatefulSetReplicas:
    return section.StatefulSetReplicas(
        desired=statefulset.spec.replicas,
        ready=statefulset.status.ready_replicas,
        updated=statefulset.status.updated_replicas,
        available=statefulset.status.available_replicas,
    )


def _info(
    statefulset: StatefulSet,
    cluster_name: str,
    kubernetes_cluster_hostname: str,
    annotation_key_pattern: AnnotationOption,
) -> section.StatefulSetInfo:
    return section.StatefulSetInfo(
        name=statefulset.metadata.name,
        namespace=statefulset.metadata.namespace,
        creation_timestamp=statefulset.metadata.creation_timestamp,
        labels=statefulset.metadata.labels,
        annotations=filter_annotations_by_key_pattern(
            statefulset.metadata.annotations, annotation_key_pattern
        ),
        selector=statefulset.spec.selector,
        containers=thin_containers(statefulset.pods),
        cluster=cluster_name,
        kubernetes_cluster_hostname=kubernetes_cluster_hostname,
    )
