#!/usr/bin/env python3
# Copyright (C) 2021 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


import itertools

import pytest
from polyfactory.factories.pydantic_factory import ModelFactory

import cmk.plugins.lib.kube
from cmk.agent_based.v2 import Metric, Result, State
from cmk.plugins.collection.agent_based import kube_cpu
from cmk.plugins.kube.schemata.section import AllocatableResource, Cpu, PerformanceUsage, Resources
from cmk.plugins.lib import kube_resources


class ResourcesFactory(ModelFactory):
    __model__ = Resources


ONE_MINUTE = 60
ONE_HOUR = 60 * ONE_MINUTE
TIMESTAMP = 359

USAGE = 0.09
ALLOCATABLE = 5.0  # value for allocatable cpu


USAGE_SECTION = PerformanceUsage(resource=Cpu(type_="cpu", usage=USAGE))


PARAMS = kube_resources.Params(
    usage="no_levels",
    request=("levels", (60.0, 90.0)),
    limit=("levels", (30.0, 45.0)),
    node=("levels", (15.0, 22.5)),
    cluster=("levels", (15.0, 22.5)),
)


RESOURCES_SECTION = Resources(
    request=0.18,
    limit=0.36,
    count_total=2,
    count_zeroed_limits=0,
    count_unspecified_limits=0,
    count_unspecified_requests=0,
)


ALLOCATABLE_RESOURCE_SECTION = AllocatableResource(context="node", value=ALLOCATABLE)


def test_discovery() -> None:
    for s1, s2, s3 in itertools.product(
        (USAGE_SECTION, None), (RESOURCES_SECTION, None), (ALLOCATABLE_RESOURCE_SECTION, None)
    ):
        assert len(list(kube_cpu.discovery_kube_cpu(s1, s2, s3))) == 1


def test_check_if_no_resources() -> None:
    """Crashing is expected, because section_kube_cpu is only missing, if data from the api
    server missing."""
    check_result = kube_cpu._check_kube_cpu(
        PARAMS, USAGE_SECTION, None, ALLOCATABLE_RESOURCE_SECTION, 1.0, {}
    )
    with pytest.raises(AssertionError):
        list(check_result)


def test_performance_cpu() -> None:
    check_result = list(
        kube_cpu._check_kube_cpu(
            PARAMS, USAGE_SECTION, RESOURCES_SECTION, ALLOCATABLE_RESOURCE_SECTION, 1.0, {}
        )
    )
    assert check_result == [
        Result(state=State.OK, summary="Usage: 0.090"),
        Metric("kube_cpu_usage", 0.09, boundaries=(0.0, None)),
        Metric("kube_cpu_request", 0.18),
        Result(
            state=State.OK,
            summary="Requests utilization: 50.00% - 0.090 of 0.180 (2/2 containers with requests)",
        ),
        Metric("kube_cpu_request_utilization", 50.0, levels=(60.0, 90.0), boundaries=(0.0, None)),
        Metric("kube_cpu_limit", 0.36),
        Result(
            state=State.OK,
            summary="Limits utilization: 25.00% - 0.090 of 0.360 (2/2 containers with limits)",
        ),
        Metric("kube_cpu_limit_utilization", 25.0, levels=(30.0, 45.0), boundaries=(0.0, None)),
        Metric("kube_cpu_allocatable", 5.0),
        Result(state=State.OK, summary="Node utilization: 1.80% - 0.090 of 5.000"),
        Metric(
            "kube_cpu_node_allocatable_utilization",
            1.8,
            levels=(15.0, 22.5),
            boundaries=(0.0, None),
        ),
    ]


def test_stored_usage_value() -> None:
    value_store = {
        "cpu_usage": (
            TIMESTAMP - ONE_MINUTE * 1,
            PerformanceUsage(resource=Cpu(type_="cpu", usage=USAGE)).model_dump_json(),
        )
    }
    performance_cpu = cmk.plugins.lib.kube_resources.performance_cpu(
        None, TIMESTAMP, value_store, "cpu_usage"
    )
    assert performance_cpu is not None


def test_stored_outdated_usage_value() -> None:
    value_store = {
        "cpu_usage": (
            TIMESTAMP - ONE_MINUTE * 2,
            PerformanceUsage(resource=Cpu(type_="cpu", usage=USAGE)).model_dump_json(),
        )
    }

    performance_cpu = cmk.plugins.lib.kube_resources.performance_cpu(
        None, TIMESTAMP, value_store, "cpu_usage"
    )
    assert performance_cpu is None
