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
    namespace_name,
    pod_resources_from_api_pods,
)
from cmk.plugins.kube.common import SectionName, WriteableSection
from cmk.plugins.kube.schemata import api, section


def create_namespace_api_sections(
    api_namespace: api.Namespace,
    namespace_api_pods: Sequence[api.Pod],
    host_settings: CheckmkHostSettings,
    piggyback_name: str,
) -> Iterator[WriteableSection]:
    yield from (
        WriteableSection(
            piggyback_name=piggyback_name,
            section_name=SectionName("kube_namespace_info_v1"),
            section=_info(
                api_namespace,
                host_settings.cluster_name,
                host_settings.annotation_key_pattern,
                host_settings.kubernetes_cluster_hostname,
            ),
        ),
        WriteableSection(
            piggyback_name=piggyback_name,
            section_name=SectionName("kube_pod_resources_v1"),
            section=pod_resources_from_api_pods(namespace_api_pods),
        ),
        WriteableSection(
            piggyback_name=piggyback_name,
            section_name=SectionName("kube_memory_resources_v1"),
            section=collect_memory_resources_from_api_pods(namespace_api_pods),
        ),
        WriteableSection(
            piggyback_name=piggyback_name,
            section_name=SectionName("kube_cpu_resources_v1"),
            section=collect_cpu_resources_from_api_pods(namespace_api_pods),
        ),
    )


def create_resource_quota_api_sections(
    resource_quota: api.ResourceQuota, piggyback_name: str
) -> Iterator[WriteableSection]:
    if (hard := resource_quota.spec.hard) is None:
        return

    if hard.memory is not None:
        yield WriteableSection(
            section_name=SectionName("kube_resource_quota_memory_resources_v1"),
            section=section.HardResourceRequirement.model_validate(hard.memory.model_dump()),
            piggyback_name=piggyback_name,
        )

    if hard.cpu is not None:
        yield WriteableSection(
            section_name=SectionName("kube_resource_quota_cpu_resources_v1"),
            section=section.HardResourceRequirement.model_validate(hard.cpu.model_dump()),
            piggyback_name=piggyback_name,
        )


def _info(
    namespace: api.Namespace,
    cluster_name: str,
    annotation_key_pattern: AnnotationOption,
    kubernetes_cluster_hostname: str,
) -> section.NamespaceInfo:
    return section.NamespaceInfo(
        name=namespace_name(namespace),
        creation_timestamp=namespace.metadata.creation_timestamp,
        labels=namespace.metadata.labels,
        annotations=filter_annotations_by_key_pattern(
            namespace.metadata.annotations, annotation_key_pattern
        ),
        cluster=cluster_name,
        kubernetes_cluster_hostname=kubernetes_cluster_hostname,
    )


def filter_matching_namespace_resource_quota(
    namespace: api.NamespaceName, resource_quotas: Sequence[api.ResourceQuota]
) -> api.ResourceQuota | None:
    for resource_quota in resource_quotas:
        if resource_quota.metadata.namespace == namespace:
            return resource_quota
    return None


def filter_pods_by_resource_quota_criteria(
    pods: Sequence[api.Pod], resource_quota: api.ResourceQuota
) -> Sequence[api.Pod]:
    resource_quota_pods = filter_pods_by_resource_quota_scopes(
        pods, resource_quota.spec.scopes or ()
    )
    return _filter_pods_by_resource_quota_scope_selector(
        resource_quota_pods, resource_quota.spec.scope_selector
    )


def _filter_pods_by_resource_quota_scope_selector(
    pods: Sequence[api.Pod], scope_selector: api.ScopeSelector | None
) -> Sequence[api.Pod]:
    if scope_selector is None:
        return pods

    return [
        pod
        for pod in pods
        if all(
            _matches_scope_selector_match_expression(pod, match_expression)
            for match_expression in scope_selector.match_expressions
        )
    ]


def _matches_scope_selector_match_expression(
    pod: api.Pod, match_expression: api.ScopedResourceMatchExpression
) -> bool:
    # TODO: add support for CrossNamespacePodAffinity
    if match_expression.scope_name in [
        api.QuotaScope.BestEffort,
        api.QuotaScope.NotBestEffort,
        api.QuotaScope.Terminating,
        api.QuotaScope.NotTerminating,
    ]:
        return _matches_quota_scope(pod, match_expression.scope_name)

    if match_expression.scope_name != api.QuotaScope.PriorityClass:
        raise NotImplementedError(
            f"The resource quota scope name {match_expression.scope_name} "
            "is currently not supported"
        )

    # XNOR case for priority class
    # if the pod has a priority class and the operator is Exists then the pod is included
    # if the pod has no priority class and the operator is DoesNotExist then the pod is included
    if match_expression.operator in (api.ScopeOperator.Exists, api.ScopeOperator.DoesNotExist):
        return not (
            (pod.spec.priority_class_name is not None)
            ^ (match_expression.operator == api.ScopeOperator.Exists)
        )

    # XNOR case for priority class value
    # if operator is In and the priority class value is in the list of values then the pod is
    # included
    # if operator is NotIn and the priority class value is not in the list of values then the pod
    # is included
    if match_expression.operator in (api.ScopeOperator.In, api.ScopeOperator.NotIn):
        return not (
            (pod.spec.priority_class_name in match_expression.values)
            ^ (match_expression.operator == api.ScopeOperator.In)
        )

    raise NotImplementedError("Unsupported match expression operator")


def filter_pods_by_resource_quota_scopes(
    api_pods: Sequence[api.Pod], scopes: Sequence[api.QuotaScope] = ()
) -> Sequence[api.Pod]:
    """Filter pods based on selected scopes"""
    return [pod for pod in api_pods if all(_matches_quota_scope(pod, scope) for scope in scopes)]


def _matches_quota_scope(pod: api.Pod, scope: api.QuotaScope) -> bool:
    """Verifies if the pod scopes matches the scope criteria

    Reminder:
    * the Quota scope is rather ResourceQuota specific rather than Pod specific
    * the Quota scope encompasses multiple Pod concepts (see api.Pod model)
    * a Pod can have all multiple scopes (e.g PrioritClass, Terminating and BestEffort)
    """

    def pod_terminating_scope(
        pod: api.Pod,
    ) -> api.QuotaScope:
        return (
            api.QuotaScope.Terminating
            if (pod.spec.active_deadline_seconds is not None)
            else api.QuotaScope.NotTerminating
        )

    def pod_effort_scope(
        pod: api.Pod,
    ) -> api.QuotaScope:
        # TODO: change qos_class from Literal to Enum
        return (
            api.QuotaScope.BestEffort
            if (pod.status.qos_class == "besteffort")
            else api.QuotaScope.NotBestEffort
        )

    if scope == api.QuotaScope.PriorityClass:
        return pod.spec.priority_class_name is not None

    if scope in [api.QuotaScope.Terminating, api.QuotaScope.NotTerminating]:
        return pod_terminating_scope(pod) == scope

    if scope in [api.QuotaScope.BestEffort, api.QuotaScope.NotBestEffort]:
        return pod_effort_scope(pod) == scope

    raise NotImplementedError(f"Unsupported quota scope {scope}")
