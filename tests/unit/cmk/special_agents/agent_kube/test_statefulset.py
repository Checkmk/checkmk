#!/usr/bin/env python3
# Copyright (C) 2022 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from typing import Sequence
from unittest.mock import MagicMock, Mock

import pytest

from tests.unit.cmk.special_agents.agent_kube.factory import (
    api_to_agent_statefulset,
    APIPodFactory,
    APIStatefulSetFactory,
    ContainerResourcesFactory,
    ContainerSpecFactory,
    PodSpecFactory,
    PodStatusFactory,
)

from cmk.special_agents import agent_kube
from cmk.special_agents.utils_kubernetes.schemata import api


def statefulsets_api_sections() -> Sequence[str]:
    return [
        "kube_pod_resources_v1",
        "kube_memory_resources_v1",
        "kube_cpu_resources_v1",
        "kube_statefulset_info_v1",
        "kube_update_strategy_v1",
        "kube_statefulset_replicas_v1",
    ]


def test_write_statefulsets_api_sections_registers_sections_to_be_written(
    write_sections_mock: MagicMock,
) -> None:
    statefulset = api_to_agent_statefulset(APIStatefulSetFactory.build())
    agent_kube.write_statefulsets_api_sections(
        "cluster", agent_kube.AnnotationNonPatternOption.ignore_all, [statefulset], "host", Mock()
    )
    assert list(write_sections_mock.call_args[0][0]) == statefulsets_api_sections()


def test_write_statefulsets_api_sections_maps_section_names_to_callables(
    write_sections_mock: MagicMock,
) -> None:
    statefulset = api_to_agent_statefulset(APIStatefulSetFactory.build())
    agent_kube.write_statefulsets_api_sections(
        "cluster", agent_kube.AnnotationNonPatternOption.ignore_all, [statefulset], "host", Mock()
    )
    assert all(
        callable(write_sections_mock.call_args[0][0][section_name])
        for section_name in statefulsets_api_sections()
    )


def test_write_statefulsets_api_sections_calls_write_sections_for_each_statefulset(
    write_sections_mock: MagicMock,
) -> None:
    statefulsets = [api_to_agent_statefulset(APIStatefulSetFactory.build()) for _ in range(3)]
    agent_kube.write_statefulsets_api_sections(
        "cluster",
        agent_kube.AnnotationNonPatternOption.ignore_all,
        statefulsets,
        "host",
        Mock(),
    )
    assert write_sections_mock.call_count == 3


@pytest.mark.parametrize("pod_number", [0, 10, 20])
def test_statefulset_pod_resources_returns_all_pods(pod_number: int) -> None:
    statefulset = api_to_agent_statefulset(
        APIStatefulSetFactory.build(),
        pods=APIPodFactory.batch(size=pod_number),
    )
    pod_resources = statefulset.pod_resources()
    assert sum(len(pods) for _, pods in pod_resources) == pod_number


def test_statefulset_pod_resources_one_pod_per_phase() -> None:
    statefulset = api_to_agent_statefulset(
        APIStatefulSetFactory.build(),
        pods=[
            APIPodFactory.build(status=PodStatusFactory.build(phase=phase)) for phase in api.Phase
        ],
    )
    pod_resources = statefulset.pod_resources()
    for _phase, pods in pod_resources:
        assert len(pods) == 1


@pytest.mark.parametrize(
    "phases", [["running"], ["pending"], ["succeeded"], ["failed"], ["unknown"]]
)
def test_statefulset_pod_resources_pods_in_phase(phases: list[str]) -> None:
    statefulset = api_to_agent_statefulset(
        APIStatefulSetFactory.build(),
        pods=[APIPodFactory.build(status=PodStatusFactory.build(phase=phase)) for phase in phases],
    )
    pods = statefulset.pods(api.Phase(phases[0]))
    assert len(pods) == 1


@pytest.mark.parametrize(
    "phases", [["running"], ["pending"], ["succeeded"], ["failed"], ["unknown"]]
)
def test_statefulset_pod_resources_pods_in_phase_no_phase_param(phases: list[str]) -> None:
    statefulset = api_to_agent_statefulset(
        APIStatefulSetFactory.build(),
        pods=[APIPodFactory.build(status=PodStatusFactory.build(phase=phase)) for phase in phases],
    )
    pods = statefulset.pods()
    assert len(pods) == len(phases)


def test_statefulset_memory_resources() -> None:
    container_resources_requirements = ContainerResourcesFactory.build(
        limits=api.ResourcesRequirements(memory=2.0 * 1024),
        requests=api.ResourcesRequirements(memory=1.0 * 1024),
    )
    container_spec = ContainerSpecFactory.build(resources=container_resources_requirements)
    api_pod = APIPodFactory.build(spec=PodSpecFactory.build(containers=[container_spec]))
    statefulset = api_to_agent_statefulset(APIStatefulSetFactory.build(), pods=[api_pod])
    memory_resources = statefulset.memory_resources()
    assert memory_resources.count_total == 1
    assert memory_resources.limit == 2.0 * 1024
    assert memory_resources.request == 1.0 * 1024


def test_statefulset_cpu_resources() -> None:
    container_resources_requirements = ContainerResourcesFactory.build(
        limits=api.ResourcesRequirements(cpu=2.0),
        requests=api.ResourcesRequirements(cpu=1.0),
    )
    container_spec = ContainerSpecFactory.build(resources=container_resources_requirements)
    api_pod = APIPodFactory.build(spec=PodSpecFactory.build(containers=[container_spec]))
    statefulset = api_to_agent_statefulset(APIStatefulSetFactory.build(), pods=[api_pod])
    cpu_resources = statefulset.cpu_resources()
    assert cpu_resources.count_total == 1
    assert cpu_resources.limit == 2.0
    assert cpu_resources.request == 1.0
