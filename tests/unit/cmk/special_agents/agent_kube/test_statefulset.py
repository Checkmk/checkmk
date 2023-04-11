#!/usr/bin/env python3
# Copyright (C) 2022 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from unittest.mock import MagicMock

import pytest

from tests.unit.cmk.special_agents.agent_kube.factory import (
    api_to_agent_statefulset,
    APIPodFactory,
    APIStatefulSetFactory,
    PodStatusFactory,
)

from cmk.special_agents import agent_kube


def statefulsets_api_sections() -> set[str]:
    return {
        "kube_pod_resources_v1",
        "kube_memory_resources_v1",
        "kube_cpu_resources_v1",
        "kube_statefulset_info_v1",
        "kube_update_strategy_v1",
        "kube_statefulset_replicas_v1",
        "kube_controller_spec_v1",
    }


def test_write_statefulsets_api_sections_registers_sections_to_be_written(
    write_writeable_sections_mock: MagicMock,
) -> None:
    statefulset = api_to_agent_statefulset(APIStatefulSetFactory.build())
    sections = agent_kube.create_statefulset_api_sections(
        statefulset,
        agent_kube.CheckmkHostSettings(
            cluster_name="cluster",
            kubernetes_cluster_hostname="host",
            annotation_key_pattern=agent_kube.AnnotationNonPatternOption.ignore_all,
        ),
        "statefulset",
    )
    agent_kube.common.write_sections(sections)

    assert write_writeable_sections_mock.call_count == 1
    assert {
        entry.section_name for entry in write_writeable_sections_mock.call_args[0][0]
    } == statefulsets_api_sections()


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
