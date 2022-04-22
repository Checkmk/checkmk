#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2022 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package

from typing import Optional

from tests.unit.cmk.special_agents.agent_kube.factory import (
    APIPodFactory,
    APIResourceQuotaFactory,
    MetaDataFactory,
    PodMetaDataFactory,
    PodSpecFactory,
    PodStatusFactory,
)

from cmk.special_agents import agent_kube as agent
from cmk.special_agents.utils_kubernetes.schemata import api


def test_filter_matching_namespace_resource_quota():
    namespace_name = api.NamespaceName("matching-namespace")
    resource_quotas = [
        APIResourceQuotaFactory.build(metadata=MetaDataFactory.build(namespace=namespace_name)),
        APIResourceQuotaFactory.build(
            metadata=MetaDataFactory.build(namespace=api.NamespaceName("non-matching-namespace"))
        ),
    ]

    matching_resource_quota = agent.filter_matching_namespace_resource_quota(
        namespace_name, resource_quotas
    )

    assert matching_resource_quota is not None
    assert matching_resource_quota.metadata.namespace == namespace_name


def test_filter_terminating_pods_by_quota_scope():
    pods = [
        _pod_with_scopes_factory(name="pod-1", terminating=True),
        _pod_with_scopes_factory(name="pod-2", terminating=False),
    ]

    terminating_pods = agent.filter_pods_by_resource_quota_scopes(
        pods, [api.QuotaScope.Terminating]
    )
    non_terminating_pods = agent.filter_pods_by_resource_quota_scopes(
        pods, [api.QuotaScope.NotTerminating]
    )

    assert [p.metadata.name for p in terminating_pods] == ["pod-1"]
    assert [p.metadata.name for p in non_terminating_pods] == ["pod-2"]


def test_filter_pods_by_best_effort_quota_scope():
    pods = [
        _pod_with_scopes_factory(name="pod-1", best_effort=True),
        _pod_with_scopes_factory(name="pod-2", best_effort=False),
    ]

    best_effort_pods = agent.filter_pods_by_resource_quota_scopes(pods, [api.QuotaScope.BestEffort])
    not_best_effort_pods = agent.filter_pods_by_resource_quota_scopes(
        pods, [api.QuotaScope.NotBestEffort]
    )

    assert [p.metadata.name for p in best_effort_pods] == ["pod-1"]
    assert [p.metadata.name for p in not_best_effort_pods] == ["pod-2"]


def test_filter_pods_with_terminating_best_effort_quota_scope():
    pods = [
        _pod_with_scopes_factory(name="pod-1", best_effort=True, terminating=True),
        _pod_with_scopes_factory(),
        _pod_with_scopes_factory(),
    ]

    terminating_best_effort_pods = agent.filter_pods_by_resource_quota_scopes(
        pods, scopes=[api.QuotaScope.Terminating, api.QuotaScope.BestEffort]
    )

    assert [p.metadata.name for p in terminating_best_effort_pods] == ["pod-1"]


def test_filter_terminating_pods_from_scope_selector_match_expression():
    """This test is equivalent to the test_filter_terminating_pods_by_quote_scope test
    but it uses a scope selector match expression instead of a scope.
    """
    pods = [
        _pod_with_scopes_factory(name="pod-1", terminating=True),
        _pod_with_scopes_factory(name="pod-2", terminating=False),
    ]

    terminating_pods = agent.filter_pods_by_resource_quota_scope_selector(
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
    non_terminating_pods = agent.filter_pods_by_resource_quota_scope_selector(
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


def test_filter_pods_with_best_effort_from_scope_selector_match_expression():
    """This test is equivalent to the test_filter_pods_by_best_effort_quota_scope test
    but it uses a scope selector match expression instead of a scope.
    """
    pods = [
        _pod_with_scopes_factory(name="pod-1", best_effort=True),
        _pod_with_scopes_factory(name="pod-2", best_effort=False),
    ]

    best_effort_pods = agent.filter_pods_by_resource_quota_scope_selector(
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
    not_best_effort_pods = agent.filter_pods_by_resource_quota_scope_selector(
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


def test_filter_terminating_best_effort_pods_from_scope_selector_match_expression():
    """This test is equivalent to the test_filter_pods_with_terminating_best_effort_quota_scope
    test but it uses a scope selector with multiple match expressions instead of scopes.
    """
    pods = [
        _pod_with_scopes_factory(name="pod-1", best_effort=True, terminating=True),
        _pod_with_scopes_factory(),
        _pod_with_scopes_factory(),
    ]

    terminating_best_effort_pods = agent.filter_pods_by_resource_quota_scope_selector(
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


def test_filter_from_scope_selector_match_expression_with_does_not_exist_operator():
    # DoesNotExist operator is only allowed for the PriorityClass scope
    # (see schemata.api.ScopedResourceMatchExpression for further details)
    pods = [
        _pod_with_scopes_factory(name="pod-1", priority_class="has-priority-class"),
        _pod_with_scopes_factory(name="pod-2"),
    ]

    no_priority_class_pods = agent.filter_pods_by_resource_quota_scope_selector(
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


def test_filter_pods_with_priority_class_from_scope_selector_match_expression():
    pods = [
        _pod_with_scopes_factory(name="pod-1", priority_class="high"),
        _pod_with_scopes_factory(name="pod-2", priority_class="medium"),
        _pod_with_scopes_factory(priority_class="low"),
    ]

    high_medium_pods = agent.filter_pods_by_resource_quota_scope_selector(
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

    high_medium_pods_from_not_in_operator = agent.filter_pods_by_resource_quota_scope_selector(
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
    name: Optional[str] = None,
    priority_class: Optional[str] = None,
    best_effort: bool = False,
    terminating: bool = False,
):
    return APIPodFactory.build(
        metadata=PodMetaDataFactory.build(name=name) if name else PodMetaDataFactory.build(),
        status=PodStatusFactory.build(qos_class="besteffort" if best_effort else "guaranteed"),
        spec=PodSpecFactory.build(
            priority_class_name=priority_class,
            active_deadline_seconds=1 if terminating else None,
        ),
    )
