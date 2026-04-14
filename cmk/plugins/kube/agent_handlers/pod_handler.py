#!/usr/bin/env python3
# Copyright (C) 2023 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from __future__ import annotations

from collections.abc import Iterator, Sequence

from cmk.plugins.kube.agent_handlers.common import (
    AnnotationOption,
    CheckmkHostSettings,
    collect_cpu_resources_from_api_pods,
    collect_memory_resources_from_api_pods,
    filter_annotations_by_key_pattern,
    kube_object_namespace_name,
    pod_lifecycle_phase,
    pod_name,
)
from cmk.plugins.kube.common import SectionName, WriteableSection
from cmk.plugins.kube.schemata import api, section


def create_api_sections(
    pod: api.Pod,
    checkmk_host_settings: CheckmkHostSettings,
    piggyback_name: str,
) -> Iterator[WriteableSection]:
    yield from (
        WriteableSection(
            piggyback_name=piggyback_name,
            section_name=SectionName("kube_pod_container_specs_v1"),
            section=_container_specs(pod.spec),
        ),
        WriteableSection(
            piggyback_name=piggyback_name,
            section_name=SectionName("kube_pod_init_container_specs_v1"),
            section=_init_container_specs(pod.spec),
        ),
        WriteableSection(
            piggyback_name=piggyback_name,
            section_name=SectionName("kube_pod_lifecycle_v1"),
            section=pod_lifecycle_phase(pod.status),
        ),
        WriteableSection(
            piggyback_name=piggyback_name,
            section_name=SectionName("kube_cpu_resources_v1"),
            section=collect_cpu_resources_from_api_pods([pod]),
        ),
        WriteableSection(
            piggyback_name=piggyback_name,
            section_name=SectionName("kube_memory_resources_v1"),
            section=collect_memory_resources_from_api_pods([pod]),
        ),
        WriteableSection(
            piggyback_name=piggyback_name,
            section_name=SectionName("kube_pod_info_v1"),
            section=_info(
                pod=pod,
                cluster_name=checkmk_host_settings.cluster_name,
                kubernetes_cluster_hostname=checkmk_host_settings.kubernetes_cluster_hostname,
                annotation_key_pattern=checkmk_host_settings.annotation_key_pattern,
            ),
        ),
    )

    if (section_conditions := _conditions(pod.status)) is not None:
        yield WriteableSection(
            piggyback_name=piggyback_name,
            section_name=SectionName("kube_pod_conditions_v1"),
            section=section_conditions,
        )

    if (section_start_time := _start_time(pod.status)) is not None:
        yield WriteableSection(
            piggyback_name=piggyback_name,
            section_name=SectionName("kube_start_time_v1"),
            section=section_start_time,
        )

    if pod.containers:
        yield WriteableSection(
            piggyback_name=piggyback_name,
            section_name=SectionName("kube_pod_containers_v1"),
            section=section.PodContainers(containers=pod.containers),
        )

    if pod.init_containers:
        yield WriteableSection(
            piggyback_name=piggyback_name,
            section_name=SectionName("kube_pod_init_containers_v1"),
            section=section.PodContainers(containers=pod.init_containers),
        )


def _conditions(pod_status: api.PodStatus) -> section.PodConditions | None:
    if pod_status.conditions is None:
        return None

    return section.PodConditions(
        **{
            condition.type.value: section.PodCondition(
                status=condition.status,
                reason=condition.reason,
                detail=condition.detail,
                last_transition_time=condition.last_transition_time,
            )
            for condition in pod_status.conditions
            if condition.type is not None
        }
    )


def _container_specs(pod_spec: api.PodSpec) -> section.ContainerSpecs:
    return _pod_container_specs(pod_spec.containers)


def _init_container_specs(pod_spec: api.PodSpec) -> section.ContainerSpecs:
    return _pod_container_specs(pod_spec.init_containers)


def _pod_container_specs(container_specs: Sequence[api.ContainerSpec]) -> section.ContainerSpecs:
    return section.ContainerSpecs(
        containers={
            spec.name: section.ContainerSpec(image_pull_policy=spec.image_pull_policy)
            for spec in container_specs
        }
    )


def _start_time(pod_status: api.PodStatus) -> section.StartTime | None:
    if pod_status.start_time is None:
        return None

    return section.StartTime(start_time=pod_status.start_time)


def _info(
    pod: api.Pod,
    cluster_name: str,
    kubernetes_cluster_hostname: str,
    annotation_key_pattern: AnnotationOption,
) -> section.PodInfo:
    return section.PodInfo(
        namespace=kube_object_namespace_name(pod),
        name=pod_name(pod),
        creation_timestamp=pod.metadata.creation_timestamp,
        labels=pod.metadata.labels,
        annotations=filter_annotations_by_key_pattern(
            pod.metadata.annotations, annotation_key_pattern
        ),
        node=pod.spec.node,
        host_network=pod.spec.host_network,
        dns_policy=pod.spec.dns_policy,
        host_ip=pod.status.host_ip,
        pod_ip=pod.status.pod_ip,
        qos_class=pod.status.qos_class,
        restart_policy=pod.spec.restart_policy,
        uid=pod.uid,
        controllers=[
            section.Controller(
                type_=c.type_,
                name=c.name,
            )
            for c in pod.controllers
        ],
        cluster=cluster_name,
        kubernetes_cluster_hostname=kubernetes_cluster_hostname,
    )
