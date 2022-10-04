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
    PodStatusFactory,
)

from cmk.special_agents import agent_kube


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


@pytest.mark.parametrize(
    "phases", [["running"], ["pending"], ["succeeded"], ["failed"], ["unknown"]]
)
def test_statefulset_pod_resources_pods_in_phase_no_phase_param(phases: list[str]) -> None:
    statefulset = api_to_agent_statefulset(
        APIStatefulSetFactory.build(),
        pods=[APIPodFactory.build(status=PodStatusFactory.build(phase=phase)) for phase in phases],
    )
    pods = statefulset.pods
    assert len(pods) == len(phases)
