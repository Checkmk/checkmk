#!/usr/bin/env python3
# Copyright (C) 2022 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from typing import Callable, Sequence
from unittest.mock import MagicMock, Mock

import pytest

from tests.unit.cmk.special_agents.agent_kube.factory import (
    api_to_agent_pod,
    api_to_agent_statefulset,
    APIPodFactory,
    APIStatefulSetFactory,
    PodStatusFactory,
)

from cmk.special_agents import agent_kube
from cmk.special_agents.utils_kubernetes.schemata import api


def test_write_statefulsets_api_sections_registers_sections_to_be_written(
    statefulsets_api_sections: Sequence[str],
    write_sections_mock: MagicMock,
) -> None:
    statefulset = api_to_agent_statefulset(APIStatefulSetFactory.build())
    agent_kube.write_statefulsets_api_sections(
        "cluster", agent_kube.AnnotationNonPatternOption.ignore_all, [statefulset], "host", Mock()
    )
    assert list(write_sections_mock.call_args[0][0]) == statefulsets_api_sections


def test_write_statefulsets_api_sections_maps_section_names_to_callables(
    statefulsets_api_sections: Sequence[str],
    write_sections_mock: MagicMock,
) -> None:
    statefulset = api_to_agent_statefulset(APIStatefulSetFactory.build())
    agent_kube.write_statefulsets_api_sections(
        "cluster", agent_kube.AnnotationNonPatternOption.ignore_all, [statefulset], "host", Mock()
    )
    assert all(
        callable(write_sections_mock.call_args[0][0][section_name])
        for section_name in statefulsets_api_sections
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
    statefulset = api_to_agent_statefulset(APIStatefulSetFactory.build())
    for _ in range(pod_number):
        statefulset.add_pod(api_to_agent_pod(APIPodFactory.build()))
    pod_resources = statefulset.pod_resources()
    assert sum(len(pods) for _, pods in pod_resources) == pod_number


def test_statefulset_pod_resources_one_pod_per_phase() -> None:
    statefulset = api_to_agent_statefulset(APIStatefulSetFactory.build())
    for phase in api.Phase:
        pod = api_to_agent_pod(APIPodFactory.build(status=PodStatusFactory.build(phase=phase)))
        statefulset.add_pod(pod)
    pod_resources = statefulset.pod_resources()
    for _phase, pods in pod_resources:
        assert len(pods) == 1


@pytest.mark.parametrize(
    "phases", [["running"], ["pending"], ["succeeded"], ["failed"], ["unknown"]]
)
def test_statefulset_pod_resources_pods_in_phase(phases: list[str]) -> None:
    statefulset = api_to_agent_statefulset(APIStatefulSetFactory.build())
    for phase in phases:
        pod = api_to_agent_pod(APIPodFactory.build(status=PodStatusFactory.build(phase=phase)))
        statefulset.add_pod(pod)
    pods = statefulset.pods(api.Phase(phases[0]))
    assert len(pods) == 1


@pytest.mark.parametrize(
    "phases", [["running"], ["pending"], ["succeeded"], ["failed"], ["unknown"]]
)
def test_statefulset_pod_resources_pods_in_phase_no_phase_param(phases: list[str]) -> None:
    statefulset = api_to_agent_statefulset(APIStatefulSetFactory.build())
    for phase in phases:
        pod = api_to_agent_pod(APIPodFactory.build(status=PodStatusFactory.build(phase=phase)))
        statefulset.add_pod(pod)
    pods = statefulset.pods()
    assert len(pods) == len(phases)


def test_statefulset_memory_resources(
    new_pod: Callable[[], agent_kube.Pod],
    pod_containers_count: int,
    container_limit_memory: float,
    container_request_memory: float,
) -> None:
    statefulset = api_to_agent_statefulset(APIStatefulSetFactory.build())
    statefulset.add_pod(new_pod())
    memory_resources = statefulset.memory_resources()
    assert memory_resources.count_total == pod_containers_count
    assert memory_resources.limit == pod_containers_count * container_limit_memory
    assert memory_resources.request == pod_containers_count * container_request_memory


def test_statefulset_cpu_resources(
    new_pod: Callable[[], agent_kube.Pod],
    pod_containers_count: int,
    container_limit_cpu: float,
    container_request_cpu: float,
) -> None:
    statefulset = api_to_agent_statefulset(APIStatefulSetFactory.build())
    statefulset.add_pod(new_pod())
    cpu_resources = statefulset.cpu_resources()
    assert cpu_resources.count_total == pod_containers_count
    assert cpu_resources.limit == pod_containers_count * container_limit_cpu
    assert cpu_resources.request == pod_containers_count * container_request_cpu
