#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2021 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from pydantic_factories import ModelFactory

from cmk.base.plugins.agent_based.agent_based_api.v1 import Metric, Result, State
from cmk.base.plugins.agent_based.kube_resource_quota_cpu import (
    check_resource_quota_resource,
    Params,
    RESOURCE_QUOTA_DEFAULT_PARAMS,
)
from cmk.base.plugins.agent_based.utils.kube import Cpu, PerformanceUsage
from cmk.base.plugins.agent_based.utils.kube_resources import (
    CPU_RENDER_FUNC,
    HardResourceRequirement,
    performance_cpu,
)


class CpuFactory(ModelFactory):
    __model__ = Cpu


class PerformanceUsageFactory(ModelFactory):
    __model__ = PerformanceUsage


class HardResourceRequirementFactory(ModelFactory):
    __model__ = HardResourceRequirement


TIMESTAMP = 359


def test_check_kube_resource_quota_cpu_with_no_resources():
    resource_usage = PerformanceUsageFactory.build(resource=CpuFactory.build(usage=1.0))

    result = tuple(
        check_resource_quota_resource(
            params=RESOURCE_QUOTA_DEFAULT_PARAMS,
            resource_usage=resource_usage,
            hard_requirement=None,
            resource_type="cpu",
            render_func=CPU_RENDER_FUNC,
        )
    )

    assert [entry.summary for entry in result if isinstance(entry, Result)] == ["Usage: 1.000"]
    assert [entry[0] for entry in result if isinstance(entry, Metric)] == ["kube_cpu_usage"]


def test_check_kube_resource_quota_cpu_with_no_usage():
    hard_requirement = HardResourceRequirementFactory.build(request=1.0, limit=2.0)

    result = tuple(
        check_resource_quota_resource(
            params=RESOURCE_QUOTA_DEFAULT_PARAMS,
            resource_usage=None,
            hard_requirement=hard_requirement,
            resource_type="cpu",
            render_func=CPU_RENDER_FUNC,
        )
    )

    assert [entry.summary for entry in result if isinstance(entry, Result)] == [
        "Requests: 1.000",
        "Limits: 2.000",
    ]
    assert [entry[0] for entry in result if isinstance(entry, Metric)] == [
        "kube_cpu_request",
        "kube_cpu_limit",
    ]


def test_check_kube_resource_quota_cpu_with_usage_and_requests_and_limits():
    hard_requirement = HardResourceRequirementFactory.build(request=1.0, limit=2.0)
    resource_usage = PerformanceUsageFactory.build(resource=CpuFactory.build(usage=1.0))

    result = tuple(
        check_resource_quota_resource(
            params=RESOURCE_QUOTA_DEFAULT_PARAMS,
            resource_usage=resource_usage,
            hard_requirement=hard_requirement,
            resource_type="cpu",
            render_func=CPU_RENDER_FUNC,
        )
    )

    assert [entry.summary for entry in result if isinstance(entry, Result)] == [
        "Usage: 1.000",
        "Requests utilization: 100.00% - 1.000 of 1.000",
        "Limits utilization: 50.00% - 1.000 of 2.000",
    ]
    assert [entry[0] for entry in result if isinstance(entry, Metric)] == [
        "kube_cpu_usage",
        "kube_cpu_request_utilization",
        "kube_cpu_limit_utilization",
    ]


def test_check_kube_resource_quota_cpu_with_usage_and_no_limits():
    hard_requirement = HardResourceRequirementFactory.build(request=1.0, limit=None)
    resource_usage = PerformanceUsageFactory.build(resource=CpuFactory.build(usage=1.0))

    result = tuple(
        check_resource_quota_resource(
            params=RESOURCE_QUOTA_DEFAULT_PARAMS,
            resource_usage=resource_usage,
            hard_requirement=hard_requirement,
            resource_type="cpu",
            render_func=CPU_RENDER_FUNC,
        )
    )

    assert [entry.summary for entry in result if isinstance(entry, Result)] == [
        "Usage: 1.000",
        "Requests utilization: 100.00% - 1.000 of 1.000",
    ]
    assert [entry[0] for entry in result if isinstance(entry, Metric)] == [
        "kube_cpu_usage",
        "kube_cpu_request_utilization",
    ]


def test_check_kube_resource_quota_cpu_with_usage_params():
    resource_usage = PerformanceUsageFactory.build(resource=CpuFactory.build(usage=1.0))

    result = tuple(
        check_resource_quota_resource(
            params=Params(
                usage=("levels", (0.6, 0.8)),  # type: ignore
                request="no_levels",
                limit="no_levels",
            ),
            resource_usage=resource_usage,
            hard_requirement=None,
            resource_type="cpu",
            render_func=CPU_RENDER_FUNC,
        )
    )

    assert [entry.state for entry in result if isinstance(entry, Result)] == [State.CRIT]
    assert [entry[0] for entry in result if isinstance(entry, Metric)] == ["kube_cpu_usage"]


def test_check_kube_resource_quota_cpu_with_request_params():
    resource_usage = PerformanceUsageFactory.build(resource=CpuFactory.build(usage=1.0))
    hard_requirement = HardResourceRequirementFactory.build(request=1.0, limit=None)

    result = tuple(
        check_resource_quota_resource(
            params=Params(
                usage="no_levels",
                request=("levels", (80.0, 90.0)),
                limit="no_levels",
            ),
            resource_usage=resource_usage,
            hard_requirement=hard_requirement,
            resource_type="cpu",
            render_func=CPU_RENDER_FUNC,
        )
    )

    assert len([entry for entry in result if isinstance(entry, Result)]) == 2
    assert isinstance(result[0], Result)
    assert result[0].state == State.OK

    assert isinstance(result[2], Result)
    assert result[2].state == State.CRIT
    assert result[2].summary.startswith("Requests utilization: 100.00%")

    assert [metric[0] for metric in result if isinstance(metric, Metric)] == [
        "kube_cpu_usage",
        "kube_cpu_request_utilization",
    ]


def test_stored_usage_value():
    performance_cpu_usage = performance_cpu(
        None,
        TIMESTAMP,
        {"resource_quota_cpu_usage": (TIMESTAMP - 59, PerformanceUsageFactory.build().json())},
        "resource_quota_cpu_usage",
    )
    assert performance_cpu_usage is not None


def test_stored_outdated_usage_value():
    performance_cpu_usage = performance_cpu(None, TIMESTAMP, {}, "resource_quota_cpu_usage")
    assert performance_cpu_usage is None
