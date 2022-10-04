#!/usr/bin/env python3
# Copyright (C) 2022 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from typing import Sequence
from unittest.mock import MagicMock, Mock

from tests.unit.cmk.special_agents.agent_kube.factory import (
    api_to_agent_daemonset,
    APIDaemonSetFactory,
    APIPodFactory,
)

from cmk.special_agents import agent_kube


def daemon_sets_api_sections() -> Sequence[str]:
    return [
        "kube_pod_resources_v1",
        "kube_memory_resources_v1",
        "kube_cpu_resources_v1",
        "kube_daemonset_info_v1",
        "kube_update_strategy_v1",
        "kube_daemonset_replicas_v1",
    ]


def test_write_daemon_sets_api_sections_registers_sections_to_be_written(
    write_sections_mock: MagicMock,
) -> None:
    daemon_set = api_to_agent_daemonset(APIDaemonSetFactory.build(), pods=[APIPodFactory.build()])
    agent_kube.write_daemon_sets_api_sections(
        "cluster",
        agent_kube.AnnotationNonPatternOption.ignore_all,
        [daemon_set],
        "host",
        Mock(),
    )
    assert list(write_sections_mock.call_args[0][0]) == daemon_sets_api_sections()


def test_write_daemon_sets_api_sections_maps_section_names_to_callables(
    write_sections_mock: MagicMock,
) -> None:
    daemon_set = api_to_agent_daemonset(APIDaemonSetFactory.build(), pods=[APIPodFactory.build()])
    agent_kube.write_daemon_sets_api_sections(
        "cluster", agent_kube.AnnotationNonPatternOption.ignore_all, [daemon_set], "host", Mock()
    )
    assert all(
        callable(write_sections_mock.call_args[0][0][section_name])
        for section_name in daemon_sets_api_sections()
    )


def test_write_daemon_sets_api_sections_calls_write_sections_for_each_daemon_set(
    write_sections_mock: MagicMock,
) -> None:
    agent_kube.write_daemon_sets_api_sections(
        "cluster",
        agent_kube.AnnotationNonPatternOption.ignore_all,
        [api_to_agent_daemonset(APIDaemonSetFactory.build()) for _ in range(3)],
        "host",
        Mock(),
    )
    assert write_sections_mock.call_count == 3
