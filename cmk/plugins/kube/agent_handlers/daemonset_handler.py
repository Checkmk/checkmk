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
    DaemonSet,
    filter_annotations_by_key_pattern,
    thin_containers,
)
from cmk.plugins.kube.common import SectionName, WriteableSection
from cmk.plugins.kube.schemata import section


def create_api_sections(
    api_daemonset: DaemonSet, host_settings: CheckmkHostSettings, piggyback_name: str
) -> Iterator[WriteableSection]:
    yield from (
        WriteableSection(
            piggyback_name=piggyback_name,
            section_name=SectionName("kube_pod_resources_v1"),
            section=api_daemonset.pod_resources(),
        ),
        WriteableSection(
            piggyback_name=piggyback_name,
            section_name=SectionName("kube_memory_resources_v1"),
            section=api_daemonset.memory_resources(),
        ),
        WriteableSection(
            piggyback_name=piggyback_name,
            section_name=SectionName("kube_cpu_resources_v1"),
            section=api_daemonset.cpu_resources(),
        ),
        WriteableSection(
            piggyback_name=piggyback_name,
            section_name=SectionName("kube_daemonset_info_v1"),
            section=_info(
                api_daemonset,
                host_settings.cluster_name,
                host_settings.kubernetes_cluster_hostname,
                host_settings.annotation_key_pattern,
            ),
        ),
        WriteableSection(
            piggyback_name=piggyback_name,
            section_name=SectionName("kube_update_strategy_v1"),
            section=controller_strategy(api_daemonset),
        ),
        WriteableSection(
            piggyback_name=piggyback_name,
            section_name=SectionName("kube_daemonset_replicas_v1"),
            section=_replicas(api_daemonset),
        ),
        WriteableSection(
            piggyback_name=piggyback_name,
            section_name=SectionName("kube_controller_spec_v1"),
            section=controller_spec(api_daemonset),
        ),
    )


def _replicas(
    daemonset: DaemonSet,
) -> section.DaemonSetReplicas:
    return section.DaemonSetReplicas(
        available=daemonset.status.number_available,
        desired=daemonset.status.desired_number_scheduled,
        updated=daemonset.status.updated_number_scheduled,
        misscheduled=daemonset.status.number_misscheduled,
        ready=daemonset.status.number_ready,
    )


def _info(
    daemonset: DaemonSet,
    cluster_name: str,
    kubernetes_cluster_hostname: str,
    annotation_key_pattern: AnnotationOption,
) -> section.DaemonSetInfo:
    return section.DaemonSetInfo(
        name=daemonset.metadata.name,
        namespace=daemonset.metadata.namespace,
        creation_timestamp=daemonset.metadata.creation_timestamp,
        labels=daemonset.metadata.labels,
        annotations=filter_annotations_by_key_pattern(
            daemonset.metadata.annotations, annotation_key_pattern
        ),
        selector=daemonset.spec.selector,
        containers=thin_containers(daemonset.pods),
        cluster=cluster_name,
        kubernetes_cluster_hostname=kubernetes_cluster_hostname,
    )
