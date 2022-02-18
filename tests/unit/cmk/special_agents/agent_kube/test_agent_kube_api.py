#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2022 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# pylint: disable=comparison-with-callable,redefined-outer-name
import pytest
from pydantic_factories import ModelFactory

from cmk.special_agents.agent_kube import Cluster
from cmk.special_agents.utils_kubernetes.schemata import api


@pytest.fixture
def node_name():
    return "node"


@pytest.fixture
def api_node(node_name):
    class APINode(ModelFactory):
        __model__ = api.Node

    node = APINode.build()
    node.metadata.name = node_name
    return node


@pytest.fixture
def api_pod(node_name):
    class APIPod(ModelFactory):
        __model__ = api.Pod

    pod = APIPod.build()
    pod.spec.node = node_name
    return pod


def test_pod_node_allocation_within_cluster(api_node, api_pod):
    """Test pod is correctly allocated to node within cluster"""
    cluster = Cluster.from_api_resources(
        pods=[api_pod],
        nodes=[api_node],
    )
    assert len(cluster.nodes()) == 1
    assert len(cluster.nodes()[0].pods()) == 1


def test_pod_deployment_allocation_within_cluster(api_node, api_pod):
    """Test pod is correctly allocated to deployment within cluster"""

    class APIDeployment(ModelFactory):
        __model__ = api.Deployment

    deployment = APIDeployment.build()
    deployment.pods = [api_pod.uid]
    cluster = Cluster.from_api_resources(
        pods=[api_pod],
        nodes=[api_node],
        deployments=[deployment],
    )
    assert len(cluster.deployments()) == 1
