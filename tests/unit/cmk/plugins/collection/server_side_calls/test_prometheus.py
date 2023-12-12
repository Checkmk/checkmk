#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
import ast
from collections.abc import Mapping

import pytest
from polyfactory.factories import DataclassFactory
from pytest_mock import MockerFixture

from cmk.plugins.collection.server_side_calls.prometheus import special_agent_prometheus
from cmk.server_side_calls.v1 import HostConfig
from cmk.special_agents.utils.prometheus import extract_connection_args


class HostConfigFactory(DataclassFactory):
    __model__ = HostConfig


@pytest.mark.parametrize(
    ["config", "host_config", "expected_result"],
    [
        pytest.param(
            {
                "connection": (
                    "ip_address",
                    {},
                ),
                "auth_basic": (
                    "auth_login",
                    {
                        "username": "user",
                        "password": (
                            "password",
                            "secret",
                        ),
                    },
                ),
                "protocol": "http",
                "host_address": "1.2.3.4",
                "host_name": "prometheus",
            },
            HostConfigFactory.build(address="1.2.3.4", name="prometheus"),
            {
                "api_url": "http://1.2.3.4/api/v1/",
                "auth": ("user", "secret"),
                "verify-cert": False,
            },
            id="explicit_login",
        ),
        pytest.param(
            {
                "connection": (
                    "url_custom",
                    {"url_address": "my-host.com"},
                ),
                "auth_basic": (
                    "auth_login",
                    {
                        "username": "user",
                        "password": (
                            "store",
                            "prometheus",
                        ),
                    },
                ),
                "protocol": "https",
                "host_address": "1.2.3.4",
                "host_name": "prometheus",
            },
            HostConfigFactory.build(address="1.2.3.4", name="prometheus"),
            {
                "auth": ("user", "very_secret"),
                "api_url": "https://my-host.com/api/v1/",
                "verify-cert": False,
            },
            id="pwstore_login",
        ),
        pytest.param(
            {
                "connection": (
                    "url_custom",
                    {"url_address": "my-host.com"},
                ),
                "auth_basic": (
                    "auth_token",
                    {
                        "token": (
                            "password",
                            "token",
                        ),
                    },
                ),
                "verify-cert": True,
                "protocol": "https",
                "host_address": "1.2.3.4",
                "host_name": "prometheus",
            },
            HostConfigFactory.build(address="1.2.3.4", name="prometheus"),
            {
                "api_url": "https://my-host.com/api/v1/",
                "token": "token",
                "verify-cert": True,
            },
            id="explicit_token",
        ),
        pytest.param(
            {
                "connection": (
                    "ip_address",
                    {
                        "port": 9876,
                        "path_prefix": "somewhere.",
                        "base_prefix": "later",
                    },
                ),
                "auth_basic": (
                    "auth_token",
                    {
                        "token": (
                            "store",
                            "prometheus",
                        ),
                    },
                ),
                "verify-cert": True,
                "protocol": "https",
                "host_address": "1.2.3.4",
                "host_name": "prometheus",
            },
            HostConfigFactory.build(address="1.2.3.4", name="prometheus"),
            {
                "api_url": "https://later1.2.3.4:9876/somewhere./api/v1/",
                "token": "very_secret",
                "verify-cert": True,
            },
            id="pwstore_token",
        ),
        pytest.param(
            {
                "connection": ("url_custom", {"url_address": "http://192.168.58.2:30000"}),
                "verify-cert": False,
                "auth_basic": (
                    "auth_login",
                    {"username": "username", "password": ("password", "password")},
                ),
                "protocol": "http",
                "exporter": [("node_exporter", {"entities": ["df", "diskstat", "mem", "kernel"]})],
                "promql_checks": [
                    {
                        "service_description": "service_name",
                        "host_name": "heute",
                        "metric_components": [
                            {
                                "metric_label": "label",
                                "metric_name": "k8s_cpu_allocatable",
                                "promql_query": "promql:query",
                                "levels": {"lower_levels": (0.0, 0.0), "upper_levels": (0.0, 0.0)},
                            }
                        ],
                    }
                ],
            },
            HostConfigFactory.build(),
            {
                "api_url": "http://http://192.168.58.2:30000/api/v1/",
                "auth": ("username", "password"),
                "verify-cert": False,
            },
            id="extensive_config",
        ),
    ],
)
def test_extract_connection_args(
    mocker: MockerFixture,
    config: Mapping[str, object],
    host_config: HostConfig,
    expected_result: Mapping[str, object],
) -> None:
    mocker.patch(
        "cmk.utils.password_store.load",
        return_value={
            "prometheus": "very_secret",
            "something_else": "123",
        },
    )
    params = special_agent_prometheus.parameter_parser(config)
    command = list(special_agent_prometheus.commands_function(params, host_config, {}))[0]
    assert isinstance(command.stdin, str)
    agent_config = ast.literal_eval(command.stdin)
    assert extract_connection_args(agent_config) == expected_result
