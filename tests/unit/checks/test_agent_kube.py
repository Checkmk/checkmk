#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from typing import Any, List, Mapping

import pytest

from tests.testlib import SpecialAgent

from cmk.base.config import SpecialAgentInfoFunctionResult

from cmk.special_agents.agent_kube import make_api_client, parse_arguments

pytestmark = pytest.mark.checks


@pytest.mark.parametrize(
    "params,expected_args",
    [
        (
            {
                "cluster-name": "cluster",
                "kubernetes-api-server": {"endpoint": ("ipaddress", {"protocol": "https"})},
                "cluster-agent": {
                    "node-ip": "11.211.3.32",
                    "connection-port": 20026,
                    "protocol": "https",
                },
                "verify-cert": False,
            },
            [
                "--cluster",
                "cluster",
                "--monitored-objects",
                "nodes",
                "deployments",
                "pods",
                "--api-server-endpoint",
                "https://127.0.0.1",
                "--cluster-agent-endpoint",
                "https://11.211.3.32:20026",
            ],
        ),
        (
            {
                "cluster-name": "cluster",
                "kubernetes-api-server": {
                    "endpoint": ("ipaddress", {"port": 8080, "protocol": "http"})
                },
                "cluster-agent": {
                    "node-ip": "11.211.3.32",
                    "connection-port": 20026,
                    "protocol": "https",
                },
                "verify-cert": True,
            },
            [
                "--cluster",
                "cluster",
                "--monitored-objects",
                "nodes",
                "deployments",
                "pods",
                "--api-server-endpoint",
                "http://127.0.0.1:8080",
                "--cluster-agent-endpoint",
                "https://11.211.3.32:20026",
                "--verify-cert",
            ],
        ),
        (
            {
                "cluster-name": "cluster",
                "monitored-objects": ["pods"],
                "kubernetes-api-server": {
                    "endpoint": ("url-custom", "http://localhost:8080"),
                    "token": ("password", "randomtoken"),
                },
                "cluster-agent": {
                    "node-ip": "11.211.3.32",
                    "connection-port": 20026,
                    "protocol": "https",
                },
                "verify-cert": False,
            },
            [
                "--cluster",
                "cluster",
                "--token",
                "randomtoken",
                "--monitored-objects",
                "pods",
                "--api-server-endpoint",
                "http://localhost:8080",
                "--cluster-agent-endpoint",
                "https://11.211.3.32:20026",
            ],
        ),
    ],
)
@pytest.mark.usefixtures("fix_register")
def test_parse_arguments(params, expected_args):
    """Tests if all required arguments are present."""
    agent = SpecialAgent("agent_kube")
    arguments = agent.argument_func(params, "host", "127.0.0.1")
    assert arguments == expected_args


def test_parse_arguments_with_no_cluster_endpoint():
    agent = SpecialAgent("agent_kube")
    params = {
        "cluster-name": "cluster",
        "kubernetes-api-server": {"endpoint": ("ipaddress", {"protocol": "https"})},
        "monitored-objects": ["pods"],
        "verify-cert": False,
    }
    arguments = agent.argument_func(params, "host", "127.0.0.1")
    assert arguments == [
        "--cluster",
        "cluster",
        "--monitored-objects",
        "pods",
        "--api-server-endpoint",
        "https://127.0.0.1",
    ]


def test_parse_namespace_patterns():
    """Tests if all required arguments are present."""
    agent = SpecialAgent("agent_kube")
    arguments = agent.argument_func(
        {
            "cluster-name": "cluster",
            "kubernetes-api-server": {"endpoint": ("ipaddress", {"protocol": "https"})},
            "cluster-agent": {
                "node-ip": "11.211.3.32",
                "connection-port": 20026,
                "protocol": "https",
            },
            "verify-cert": False,
            "namespaces": ("namespace-include-patterns", ["default", "kube-system"]),
        },
        "host",
        "127.0.0.1",
    )
    assert arguments == [
        "--cluster",
        "cluster",
        "--monitored-objects",
        "nodes",
        "deployments",
        "pods",
        "--namespace-include-patterns",
        "default",
        "--namespace-include-patterns",
        "kube-system",
        "--api-server-endpoint",
        "https://127.0.0.1",
        "--cluster-agent-endpoint",
        "https://11.211.3.32:20026",
    ]


@pytest.mark.parametrize(
    "params, host",
    [
        (
            {
                "cluster-name": "test",
                "kubernetes-api-server": {"endpoint": ("ipaddress", {"protocol": "https"})},
                "cluster-agent": {
                    "node-ip": "11.211.3.32",
                    "connection-port": 20026,
                    "protocol": "https",
                },
                "verify-cert": False,
            },
            "https://127.0.0.1",
        ),
        (
            {
                "cluster-name": "test",
                "kubernetes-api-server": {
                    "endpoint": ("ipaddress", {"port": 8080, "protocol": "http"})
                },
                "cluster-agent": {
                    "node-ip": "11.211.3.32",
                    "connection-port": 20026,
                    "protocol": "https",
                },
                "verify-cert": True,
            },
            "http://127.0.0.1:8080",
        ),
        (
            {
                "cluster-name": "test",
                "kubernetes-api-server": {
                    "endpoint": ("url-custom", "http://localhost:8080"),
                    "token": ("password", "randomtoken"),
                },
                "cluster-agent": {
                    "node-ip": "11.211.3.32",
                    "connection-port": 20026,
                    "protocol": "https",
                },
                "verify-cert": False,
            },
            "http://localhost:8080",
        ),
    ],
)
@pytest.mark.usefixtures("fix_register")
def test_client_configuration_host(params: Mapping[str, Any], host) -> None:
    agent = SpecialAgent("agent_kube")
    arguments: List[str] = []
    argument_raw: SpecialAgentInfoFunctionResult = agent.argument_func(params, "kubi", "127.0.0.1")
    # this does not feel right:
    assert isinstance(argument_raw, list)
    for element in argument_raw:
        assert isinstance(element, str)
        arguments.append(element)

    client = make_api_client(parse_arguments(arguments))
    assert client.configuration.host == host
