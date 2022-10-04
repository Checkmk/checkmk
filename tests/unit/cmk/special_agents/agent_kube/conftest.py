#!/usr/bin/env python3
# Copyright (C) 2022 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


####################################################################################
# NOTE: This is considered as a workaround file and is intended to removed
# in the future.
####################################################################################


import unittest
from typing import Sequence

import pytest
import pytest_mock

# pylint: disable=comparison-with-callable,redefined-outer-name


@pytest.fixture
def nodes_api_sections() -> Sequence[str]:
    return [
        "kube_node_container_count_v1",
        "kube_node_kubelet_v1",
        "kube_pod_resources_v1",
        "kube_allocatable_pods_v1",
        "kube_node_info_v1",
        "kube_cpu_resources_v1",
        "kube_memory_resources_v1",
        "kube_allocatable_cpu_resource_v1",
        "kube_allocatable_memory_resource_v1",
        "kube_node_conditions_v1",
        "kube_node_custom_conditions_v1",
    ]


@pytest.fixture
def cluster_api_sections() -> Sequence[str]:
    return [
        "kube_pod_resources_v1",
        "kube_allocatable_pods_v1",
        "kube_node_count_v1",
        "kube_cluster_details_v1",
        "kube_memory_resources_v1",
        "kube_cpu_resources_v1",
        "kube_allocatable_memory_resource_v1",
        "kube_allocatable_cpu_resource_v1",
        "kube_cluster_info_v1",
        "kube_collector_daemons_v1",
    ]


@pytest.fixture
def deployments_api_sections() -> Sequence[str]:
    return [
        "kube_pod_resources_v1",
        "kube_memory_resources_v1",
        "kube_deployment_info_v1",
        "kube_deployment_conditions_v1",
        "kube_cpu_resources_v1",
        "kube_update_strategy_v1",
        "kube_deployment_replicas_v1",
    ]


@pytest.fixture
def daemon_sets_api_sections() -> Sequence[str]:
    return [
        "kube_pod_resources_v1",
        "kube_memory_resources_v1",
        "kube_cpu_resources_v1",
        "kube_daemonset_info_v1",
        "kube_update_strategy_v1",
        "kube_daemonset_replicas_v1",
    ]


@pytest.fixture
def statefulsets_api_sections() -> Sequence[str]:
    return [
        "kube_pod_resources_v1",
        "kube_memory_resources_v1",
        "kube_cpu_resources_v1",
        "kube_statefulset_info_v1",
        "kube_update_strategy_v1",
        "kube_statefulset_replicas_v1",
    ]


@pytest.fixture
def write_sections_mock(mocker: pytest_mock.MockFixture) -> unittest.mock.MagicMock:
    return mocker.patch("cmk.special_agents.agent_kube._write_sections")
