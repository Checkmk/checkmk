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
                "kubernetes-api-server": {"endpoint": ("ipaddress", {"protocol": "https"})},
                "cluster-agent": {
                    "node_ip": "11.211.3.32",
                    "connection_port": 20026,
                    "protocol": "https",
                },
                "verify-cert": False,
            },
            [
                "--monitored-objects",
                "nodes deployments pods",
                "--api-server-endpoint",
                "https://127.0.0.1",
                "--cluster-agent-endpoint",
                "https://11.211.3.32:20026",
            ],
        ),
        (
            {
                "kubernetes-api-server": {
                    "endpoint": ("ipaddress", {"port": 8080, "protocol": "http"})
                },
                "cluster-agent": {
                    "node_ip": "11.211.3.32",
                    "connection_port": 20026,
                    "protocol": "https",
                },
                "verify-cert": True,
            },
            [
                "--monitored-objects",
                "nodes deployments pods",
                "--api-server-endpoint",
                "http://127.0.0.1:8080",
                "--cluster-agent-endpoint",
                "https://11.211.3.32:20026",
                "--verify-cert",
            ],
        ),
        (
            {
                "monitored_objects": ["pods"],
                "kubernetes-api-server": {
                    "endpoint": ("url_custom", "http://localhost:8080"),
                    "token": ("password", "randomtoken"),
                },
                "cluster-agent": {
                    "node_ip": "11.211.3.32",
                    "connection_port": 20026,
                    "protocol": "https",
                },
                "verify-cert": False,
            },
            [
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


@pytest.mark.parametrize(
    "params, host",
    [
        (
            {
                "kubernetes-api-server": {"endpoint": ("ipaddress", {"protocol": "https"})},
                "cluster-agent": {
                    "node_ip": "11.211.3.32",
                    "connection_port": 20026,
                    "protocol": "https",
                },
                "verify-cert": False,
            },
            "https://127.0.0.1",
        ),
        (
            {
                "kubernetes-api-server": {
                    "endpoint": ("ipaddress", {"port": 8080, "protocol": "http"})
                },
                "cluster-agent": {
                    "node_ip": "11.211.3.32",
                    "connection_port": 20026,
                    "protocol": "https",
                },
                "verify-cert": True,
            },
            "http://127.0.0.1:8080",
        ),
        (
            {
                "kubernetes-api-server": {
                    "endpoint": ("url_custom", "http://localhost:8080"),
                    "token": ("password", "randomtoken"),
                },
                "cluster-agent": {
                    "node_ip": "11.211.3.32",
                    "connection_port": 20026,
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
