#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from typing import Any, List, Mapping

import pytest

from tests.testlib import SpecialAgent

from cmk.base.config import SpecialAgentInfoFunctionResult

from cmk.special_agents.agent_kubernetes import get_api_client, parse_arguments

pytestmark = pytest.mark.checks


@pytest.mark.parametrize(
    "params,expected_args",
    [
        (
            {
                "api-server-endpoint": ("url_custom", "https://amazon.region1.com"),
                "token": ("password", "XYZ"),
                "no-cert-check": False,
                "namespaces": False,
                "infos": ["nodes", "services", "pods"],
            },
            [
                "--token",
                "XYZ",
                "--infos",
                "nodes,services,pods",
                "--api-server-endpoint",
                "https://amazon.region1.com",
            ],
        ),
        (
            {
                "api-server-endpoint": ("hostname", {}),
                "token": ("password", "XYZ"),
            },
            [
                "--token",
                "XYZ",
                "--infos",
                "nodes",
                "--api-server-endpoint",
                "https://host",
            ],
        ),
        (
            {
                "api-server-endpoint": (
                    "ipaddress",
                    {
                        "port": 522,
                        "path-prefix": "/some/prefix",
                    },
                ),
                "token": ("password", "XYZ"),
            },
            [
                "--token",
                "XYZ",
                "--infos",
                "nodes",
                "--api-server-endpoint",
                "https://127.0.0.1",
                "--port",
                "522",
                "--path-prefix",
                "/some/prefix",
            ],
        ),
    ],
)
@pytest.mark.usefixtures("fix_register")
def test_parse_arguments(params, expected_args) -> None:
    """Tests if all required arguments are present."""
    agent = SpecialAgent("agent_kubernetes")
    arguments = agent.argument_func(params, "host", "127.0.0.1")
    assert arguments == expected_args


@pytest.mark.parametrize(
    "params, host",
    [
        (
            {
                "api-server-endpoint": (
                    "url_custom",
                    "https://10.10.10.10:6433/",
                ),
                "token": ("password", "XYZ"),
                "namespaces": False,
            },
            "https://10.10.10.10:6433/",
        ),
        (
            {
                "api-server-endpoint": (
                    "ipaddress",
                    {
                        "port": 6433,
                        "path-prefix": "/some/prefix",
                    },
                ),
                "token": ("password", "XYZ"),
            },
            "https://192.168.1.1:6433/some/prefix",
        ),
        (
            {
                "api-server-endpoint": ("ipaddress", {}),
                "token": ("password", "XYZ"),
            },
            "https://192.168.1.1",
        ),
        (
            {
                "api-server-endpoint": (
                    "hostname",
                    {
                        "port": 6433,
                    },
                ),
                "token": ("password", "XYZ"),
            },
            "https://a-host-name:6433",
        ),
        (
            {
                "api-server-endpoint": ("hostname", {}),
                "token": ("password", "XYZ"),
            },
            "https://a-host-name",
        ),
    ],
)
@pytest.mark.usefixtures("fix_register")
def test_client_configuration_host(params: Mapping[str, Any], host: str) -> None:
    # black box test: wato config and corresponding url that is used by the special agent to query k8s
    agent = SpecialAgent("agent_kubernetes")
    arguments: List[str] = []
    argument_raw: SpecialAgentInfoFunctionResult = agent.argument_func(
        params, "a-host-name", "192.168.1.1"
    )
    # this does not feel right:
    assert isinstance(argument_raw, list)
    for element in argument_raw:
        assert isinstance(element, str)
        arguments.append(element)

    client = get_api_client(parse_arguments(arguments))
    assert client.configuration.host == host
