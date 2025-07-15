#!/usr/bin/env python3
# Copyright (C) 2022 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.plugins.kube.agent_handlers.common import AnnotationNonPatternOption, CheckmkHostSettings
from cmk.plugins.kube.agent_handlers.namespace_handler import (
    _filter_pods_by_resource_quota_scope_selector,
    create_namespace_api_sections,
    create_resource_quota_api_sections,
    filter_matching_namespace_resource_quota,
    filter_pods_by_resource_quota_scopes,
)
from cmk.plugins.kube.schemata import api
from tests.unit.cmk.plugins.kube.agent_kube.factory import (
    APINamespaceFactory,
    APIPodFactory,
    APIResourceQuotaFactory,
    MetaDataFactory,
    PodSpecFactory,
    PodStatusFactory,
)


def test_namespace_create_api_sections() -> None:
    namespace = APINamespaceFactory.build()
    sections = create_namespace_api_sections(
        namespace,
        APIPodFactory.batch(1),
        CheckmkHostSettings(
            cluster_name="cluster",
            kubernetes_cluster_hostname="host",
            annotation_key_pattern=AnnotationNonPatternOption.ignore_all,
        ),
        "namespace",
    )
    assert {s.section_name for s in sections} == {
        "kube_namespace_info_v1",
        "kube_pod_resources_v1",
        "kube_memory_resources_v1",
        "kube_cpu_resources_v1",
    }


def test_resource_quota_write_api_sections() -> None:
    resource_quota = APIResourceQuotaFactory.build(
        spec=api.ResourceQuotaSpec(
            hard=api.HardRequirement(
                cpu=api.HardResourceRequirement(limit=1.0, request=0.8),
                memory=api.HardResourceRequirement(limit=10.0, request=10.0),
            )
        )
    )
    sections = create_resource_quota_api_sections(
        resource_quota,
        "namespace",
    )
    assert {s.section_name for s in sections} == {
        "kube_resource_quota_cpu_resources_v1",
        "kube_resource_quota_memory_resources_v1",
    }


def test_resource_quota_write_partial_sections() -> None:
    resource_quota = APIResourceQuotaFactory.build(
        spec=api.ResourceQuotaSpec(
            hard=api.HardRequirement(
                cpu=None,
                memory=api.HardResourceRequirement(limit=10.0, request=10.0),
            )
        )
    )
    sections = create_resource_quota_api_sections(
        resource_quota,
        "namespace",
    )
    assert {s.section_name for s in sections} == {
        "kube_resource_quota_memory_resources_v1",
    }


def test_filter_matching_namespace_resource_quota() -> None:
    namespace_name = api.NamespaceName("matching-namespace")
    resource_quotas = [
        APIResourceQuotaFactory.build(
            metadata=MetaDataFactory.build(namespace=namespace_name, factory_use_construct=True)
        ),
        APIResourceQuotaFactory.build(
            metadata=MetaDataFactory.build(
                namespace=api.NamespaceName("non-matching-namespace"), factory_use_construct=True
            )
        ),
    ]

    matching_resource_quota = filter_matching_namespace_resource_quota(
        namespace_name, resource_quotas
    )

    assert matching_resource_quota is not None
    assert matching_resource_quota.metadata.namespace == namespace_name


def test_filter_terminating_pods_by_quota_scope() -> None:
    pods = [
        _pod_with_scopes_factory(name="pod-1", terminating=True),
        _pod_with_scopes_factory(name="pod-2", terminating=False),
    ]

    terminating_pods = filter_pods_by_resource_quota_scopes(pods, [api.QuotaScope.Terminating])
    non_terminating_pods = filter_pods_by_resource_quota_scopes(
        pods, [api.QuotaScope.NotTerminating]
    )

    assert [p.metadata.name for p in terminating_pods] == ["pod-1"]
    assert [p.metadata.name for p in non_terminating_pods] == ["pod-2"]


def test_filter_pods_by_best_effort_quota_scope() -> None:
    pods = [
        _pod_with_scopes_factory(name="pod-1", best_effort=True),
        _pod_with_scopes_factory(name="pod-2", best_effort=False),
    ]

    best_effort_pods = filter_pods_by_resource_quota_scopes(pods, [api.QuotaScope.BestEffort])
    not_best_effort_pods = filter_pods_by_resource_quota_scopes(
        pods, [api.QuotaScope.NotBestEffort]
    )

    assert [p.metadata.name for p in best_effort_pods] == ["pod-1"]
    assert [p.metadata.name for p in not_best_effort_pods] == ["pod-2"]


def test_filter_pods_with_terminating_best_effort_quota_scope() -> None:
    pods = [
        _pod_with_scopes_factory(name="pod-1", best_effort=True, terminating=True),
        _pod_with_scopes_factory(),
        _pod_with_scopes_factory(),
    ]

    terminating_best_effort_pods = filter_pods_by_resource_quota_scopes(
        pods, scopes=[api.QuotaScope.Terminating, api.QuotaScope.BestEffort]
    )

    assert [p.metadata.name for p in terminating_best_effort_pods] == ["pod-1"]


def test_filter_terminating_pods_from_scope_selector_match_expression() -> None:
    """This test is equivalent to the test_filter_terminating_pods_by_quote_scope test
    but it uses a scope selector match expression instead of a scope.
    """
    pods = [
        _pod_with_scopes_factory(name="pod-1", terminating=True),
        _pod_with_scopes_factory(name="pod-2", terminating=False),
    ]

    terminating_pods = _filter_pods_by_resource_quota_scope_selector(
        pods,
        api.ScopeSelector(
            match_expressions=[
                api.ScopedResourceMatchExpression(
                    operator=api.ScopeOperator.Exists,
                    scope_name=api.QuotaScope.Terminating,
                    values=[],
                )
            ]
        ),
    )
    non_terminating_pods = _filter_pods_by_resource_quota_scope_selector(
        pods,
        api.ScopeSelector(
            match_expressions=[
                api.ScopedResourceMatchExpression(
                    operator=api.ScopeOperator.Exists,
                    scope_name=api.QuotaScope.NotTerminating,
                    values=[],
                )
            ]
        ),
    )

    assert [p.metadata.name for p in terminating_pods] == ["pod-1"]
    assert [p.metadata.name for p in non_terminating_pods] == ["pod-2"]


def test_filter_pods_with_best_effort_from_scope_selector_match_expression() -> None:
    """This test is equivalent to the test_filter_pods_by_best_effort_quota_scope test
    but it uses a scope selector match expression instead of a scope.
    """
    pods = [
        _pod_with_scopes_factory(name="pod-1", best_effort=True),
        _pod_with_scopes_factory(name="pod-2", best_effort=False),
    ]

    best_effort_pods = _filter_pods_by_resource_quota_scope_selector(
        pods,
        api.ScopeSelector(
            match_expressions=[
                api.ScopedResourceMatchExpression(
                    operator=api.ScopeOperator.Exists,
                    scope_name=api.QuotaScope.BestEffort,
                    values=[],
                )
            ]
        ),
    )
    not_best_effort_pods = _filter_pods_by_resource_quota_scope_selector(
        pods,
        api.ScopeSelector(
            match_expressions=[
                api.ScopedResourceMatchExpression(
                    operator=api.ScopeOperator.Exists,
                    scope_name=api.QuotaScope.NotBestEffort,
                    values=[],
                )
            ]
        ),
    )

    assert [p.metadata.name for p in best_effort_pods] == ["pod-1"]
    assert [p.metadata.name for p in not_best_effort_pods] == ["pod-2"]


def test_filter_terminating_best_effort_pods_from_scope_selector_match_expression() -> None:
    """This test is equivalent to the test_filter_pods_with_terminating_best_effort_quota_scope
    test but it uses a scope selector with multiple match expressions instead of scopes.
    """
    pods = [
        _pod_with_scopes_factory(name="pod-1", best_effort=True, terminating=True),
        _pod_with_scopes_factory(),
        _pod_with_scopes_factory(),
    ]

    terminating_best_effort_pods = _filter_pods_by_resource_quota_scope_selector(
        pods,
        api.ScopeSelector(
            match_expressions=[
                api.ScopedResourceMatchExpression(
                    operator=api.ScopeOperator.Exists,
                    scope_name=api.QuotaScope.Terminating,
                    values=[],
                ),
                api.ScopedResourceMatchExpression(
                    operator=api.ScopeOperator.Exists,
                    scope_name=api.QuotaScope.BestEffort,
                    values=[],
                ),
            ]
        ),
    )

    assert [p.metadata.name for p in terminating_best_effort_pods] == ["pod-1"]


def test_filter_from_scope_selector_match_expression_with_does_not_exist_operator() -> None:
    # DoesNotExist operator is only allowed for the PriorityClass scope
    # (see schemata.api.ScopedResourceMatchExpression for further details)
    pods = [
        _pod_with_scopes_factory(name="pod-1", priority_class="has-priority-class"),
        _pod_with_scopes_factory(name="pod-2"),
    ]

    no_priority_class_pods = _filter_pods_by_resource_quota_scope_selector(
        pods,
        api.ScopeSelector(
            match_expressions=[
                api.ScopedResourceMatchExpression(
                    operator=api.ScopeOperator.DoesNotExist,
                    scope_name=api.QuotaScope.PriorityClass,
                    values=[],
                ),
            ]
        ),
    )

    assert [p.metadata.name for p in no_priority_class_pods] == ["pod-2"]


def test_filter_pods_with_priority_class_from_scope_selector_match_expression() -> None:
    pods = [
        _pod_with_scopes_factory(name="pod-1", priority_class="high"),
        _pod_with_scopes_factory(name="pod-2", priority_class="medium"),
        _pod_with_scopes_factory(priority_class="low"),
    ]

    high_medium_pods = _filter_pods_by_resource_quota_scope_selector(
        pods,
        api.ScopeSelector(
            match_expressions=[
                api.ScopedResourceMatchExpression(
                    operator=api.ScopeOperator.In,
                    scope_name=api.QuotaScope.PriorityClass,
                    values=["high", "medium"],
                )
            ]
        ),
    )

    high_medium_pods_from_not_in_operator = _filter_pods_by_resource_quota_scope_selector(
        pods,
        api.ScopeSelector(
            match_expressions=[
                api.ScopedResourceMatchExpression(
                    operator=api.ScopeOperator.NotIn,
                    scope_name=api.QuotaScope.PriorityClass,
                    values=["low"],
                )
            ]
        ),
    )

    assert [p.metadata.name for p in high_medium_pods] == ["pod-1", "pod-2"]
    assert [p.metadata.name for p in high_medium_pods_from_not_in_operator] == ["pod-1", "pod-2"]


def _pod_with_scopes_factory(
    name: str | None = None,
    priority_class: str | None = None,
    best_effort: bool = False,
    terminating: bool = False,
) -> api.Pod:
    return APIPodFactory.build(
        metadata=(
            MetaDataFactory.build(name=name, factory_use_construct=True)
            if name
            else MetaDataFactory.build(factory_use_construct=True)
        ),
        status=PodStatusFactory.build(qos_class="besteffort" if best_effort else "guaranteed"),
        spec=PodSpecFactory.build(
            priority_class_name=priority_class,
            active_deadline_seconds=1 if terminating else None,
        ),
    )
