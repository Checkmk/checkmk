#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2022 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from unittest.mock import Mock

import pytest

from cmk.special_agents import agent_kube
from cmk.special_agents.utils_kubernetes.schemata import section


def test_write_daemon_sets_api_sections_registers_sections_to_be_written(
    daemon_set, daemon_sets_api_sections, write_sections_mock
):
    agent_kube.write_daemon_sets_api_sections(
        "cluster",
        agent_kube.AnnotationNonPatternOption.ignore_all,
        [daemon_set],
        Mock(),
    )
    assert list(write_sections_mock.call_args[0][0]) == daemon_sets_api_sections


def test_write_daemon_sets_api_sections_maps_section_names_to_callables(
    daemon_set, daemon_sets_api_sections, write_sections_mock
):
    agent_kube.write_daemon_sets_api_sections(
        "cluster", agent_kube.AnnotationNonPatternOption.ignore_all, [daemon_set], Mock()
    )
    assert all(
        callable(write_sections_mock.call_args[0][0][section_name])
        for section_name in daemon_sets_api_sections
    )


def test_write_daemon_sets_api_sections_calls_write_sections_for_each_daemon_set(
    new_daemon_set, write_sections_mock
):
    agent_kube.write_daemon_sets_api_sections(
        "cluster",
        agent_kube.AnnotationNonPatternOption.ignore_all,
        [new_daemon_set() for _ in range(3)],
        Mock(),
    )
    assert write_sections_mock.call_count == 3


@pytest.mark.parametrize("daemon_set_pods", [0, 10, 20])
def test_daemon_set_pod_resources_returns_all_pods(daemon_set, daemon_set_pods) -> None:
    resources = dict(daemon_set.pod_resources())
    pod_resources = section.PodResources(**resources)
    assert sum(len(pods) for _, pods in pod_resources) == daemon_set_pods


def test_daemon_set_pod_resources_one_pod_per_phase(daemon_set) -> None:
    resources = dict(daemon_set.pod_resources())
    pod_resources = section.PodResources(**resources)
    for _phase, pods in pod_resources:
        assert len(pods) == 1


@pytest.mark.parametrize(
    "phases", [["running"], ["pending"], ["succeeded"], ["failed"], ["unknown"]]
)
def test_daemon_set_pod_resources_pods_in_phase(daemon_set, phases, daemon_set_pods) -> None:
    pods = daemon_set.pods(phases[0])
    assert len(pods) == daemon_set_pods


@pytest.mark.parametrize(
    "phases", [["running"], ["pending"], ["succeeded"], ["failed"], ["unknown"]]
)
def test_daemon_set_pod_resources_pods_in_phase_no_phase_param(daemon_set, daemon_set_pods) -> None:
    pods = daemon_set.pods()
    assert len(pods) == daemon_set_pods


def test_daemon_set_memory_resources(
    new_daemon_set, new_pod, pod_containers_count, container_limit_memory, container_request_memory
):
    daemon_set = new_daemon_set()
    daemon_set.add_pod(new_pod())
    memory_resources = daemon_set.memory_resources()
    assert memory_resources.count_total == pod_containers_count
    assert memory_resources.limit == pod_containers_count * container_limit_memory
    assert memory_resources.request == pod_containers_count * container_request_memory


def test_daemon_set_cpu_resources(
    new_daemon_set, new_pod, pod_containers_count, container_limit_cpu, container_request_cpu
):
    daemon_set = new_daemon_set()
    daemon_set.add_pod(new_pod())
    cpu_resources = daemon_set.cpu_resources()
    assert cpu_resources.count_total == pod_containers_count
    assert cpu_resources.limit == pod_containers_count * container_limit_cpu
    assert cpu_resources.request == pod_containers_count * container_request_cpu
