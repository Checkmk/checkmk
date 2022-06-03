#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2021 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from pydantic_factories import ModelFactory

from cmk.base.plugins.agent_based.agent_based_api.v1 import Metric, Result, State
from cmk.base.plugins.agent_based.kube_resource_quota_memory import (
    check_resource_quota_resource,
    Params,
    render,
    RESOURCE_QUOTA_DEFAULT_PARAMS,
)
from cmk.base.plugins.agent_based.utils.kube import Memory, PerformanceUsage
from cmk.base.plugins.agent_based.utils.kube_resources import HardResourceRequirement


class MemoryFactory(ModelFactory):
    __model__ = Memory


class PerformanceUsageFactory(ModelFactory):
    __model__ = PerformanceUsage


class HardResourceRequirementFactory(ModelFactory):
    __model__ = HardResourceRequirement


def test_check_kube_resource_quota_memory_with_no_resources():
    resource_usage = PerformanceUsageFactory.build(resource=MemoryFactory.build(usage=1000.0))

    result = tuple(
        check_resource_quota_resource(
            params=RESOURCE_QUOTA_DEFAULT_PARAMS,
            resource_usage=resource_usage,
            hard_requirement=None,
            resource_type="memory",
            render_func=render.bytes,
        )
    )

    assert [entry.summary for entry in result if isinstance(entry, Result)] == ["Usage: 1000 B"]
    assert [entry[0] for entry in result if isinstance(entry, Metric)] == ["kube_memory_usage"]


def test_check_kube_resource_quota_memory_with_no_usage():
    hard_requirement = HardResourceRequirementFactory.build(request=1000.0, limit=2000.0)

    result = tuple(
        check_resource_quota_resource(
            params=RESOURCE_QUOTA_DEFAULT_PARAMS,
            resource_usage=None,
            hard_requirement=hard_requirement,
            resource_type="memory",
            render_func=render.bytes,
        )
    )

    assert [entry.summary for entry in result if isinstance(entry, Result)] == [
        "Requests: 1000 B",
        "Limits: 1.95 KiB",
    ]
    assert [entry[0] for entry in result if isinstance(entry, Metric)] == [
        "kube_memory_request",
        "kube_memory_limit",
    ]


def test_check_kube_resource_quota_memory_with_usage_and_requests_and_limits():
    hard_requirement = HardResourceRequirementFactory.build(request=1000.0, limit=2000.0)
    resource_usage = PerformanceUsageFactory.build(resource=MemoryFactory.build(usage=1000.0))

    result = tuple(
        check_resource_quota_resource(
            params=RESOURCE_QUOTA_DEFAULT_PARAMS,
            resource_usage=resource_usage,
            hard_requirement=hard_requirement,
            resource_type="memory",
            render_func=render.bytes,
        )
    )

    assert [entry.summary for entry in result if isinstance(entry, Result)] == [
        "Usage: 1000 B",
        "Requests utilization: 100.00% - 1000 B of 1000 B",
        "Limits utilization: 50.00% - 1000 B of 1.95 KiB",
    ]
    assert [entry[0] for entry in result if isinstance(entry, Metric)] == [
        "kube_memory_usage",
        "kube_memory_request_utilization",
        "kube_memory_limit_utilization",
    ]


def test_check_kube_resource_quota_memory_with_usage_and_no_limits():
    hard_requirement = HardResourceRequirementFactory.build(request=1000.0, limit=None)
    resource_usage = PerformanceUsageFactory.build(resource=MemoryFactory.build(usage=1000.0))

    result = tuple(
        check_resource_quota_resource(
            params=RESOURCE_QUOTA_DEFAULT_PARAMS,
            resource_usage=resource_usage,
            hard_requirement=hard_requirement,
            resource_type="memory",
            render_func=render.bytes,
        )
    )

    assert [entry.summary for entry in result if isinstance(entry, Result)] == [
        "Usage: 1000 B",
        "Requests utilization: 100.00% - 1000 B of 1000 B",
    ]
    assert [entry[0] for entry in result if isinstance(entry, Metric)] == [
        "kube_memory_usage",
        "kube_memory_request_utilization",
    ]


def test_check_kube_resource_quota_memory_with_usage_params():
    resource_usage = PerformanceUsageFactory.build(resource=MemoryFactory.build(usage=1000.0))

    result = tuple(
        check_resource_quota_resource(
            params=Params(
                usage=("levels", (500.0, 600.0)),
                request="no_levels",
                limit="no_levels",
            ),
            resource_usage=resource_usage,
            hard_requirement=None,
            resource_type="memory",
            render_func=render.bytes,
        )
    )

    assert [entry.state for entry in result if isinstance(entry, Result)] == [State.CRIT]
    assert [entry[0] for entry in result if isinstance(entry, Metric)] == ["kube_memory_usage"]


def test_check_kube_resource_quota_memory_with_request_params():
    resource_usage = PerformanceUsageFactory.build(resource=MemoryFactory.build(usage=1000.0))
    hard_requirement = HardResourceRequirementFactory.build(request=1000.0, limit=None)

    result = tuple(
        check_resource_quota_resource(
            params=Params(
                usage="no_levels",
                request=("levels", (80.0, 90.0)),
                limit="no_levels",
            ),
            resource_usage=resource_usage,
            hard_requirement=hard_requirement,
            resource_type="memory",
            render_func=render.bytes,
        )
    )

    assert len([entry for entry in result if isinstance(entry, Result)]) == 2
    assert isinstance(result[0], Result)
    assert result[0].state == State.OK

    assert isinstance(result[2], Result)
    assert result[2].state == State.CRIT
    assert result[2].summary.startswith("Requests utilization: 100.00%")

    assert [metric[0] for metric in result if isinstance(metric, Metric)] == [
        "kube_memory_usage",
        "kube_memory_request_utilization",
    ]
