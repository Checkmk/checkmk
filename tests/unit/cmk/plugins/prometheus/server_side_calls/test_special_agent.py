#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Mapping

import pytest

from cmk.plugins.prometheus.server_side_calls.special_agent import special_agent_prometheus
from cmk.server_side_calls.v1 import HostConfig, IPv4Config, Secret, SpecialAgentCommand


@pytest.mark.parametrize(
    ["raw_params", "host_config", "expected_result"],
    [
        pytest.param(
            {
                "connection": "prometheus-server",
                "verify_cert": False,
                "protocol": "http",
                "exporter": [],
                "promql_checks": [],
            },
            HostConfig(
                name="host",
                ipv4_config=IPv4Config(address="1.2.3.4"),
            ),
            SpecialAgentCommand(
                stdin=(
                    "{'connection': 'prometheus-server', 'protocol': "
                    "'http', 'exporter': [], 'promql_checks': [], "
                    "'host_address': '1.2.3.4', 'host_name': 'host'}"
                ),
                command_arguments=["--disable-cert-verification"],
            ),
            id="minimal configuration",
        ),
        pytest.param(
            {
                "connection": "$HOSTNAME$",
                "verify_cert": False,
                "protocol": "http",
                "exporter": [],
                "promql_checks": [],
            },
            HostConfig(
                name="host",
                ipv4_config=IPv4Config(address="1.2.3.4"),
                macros={
                    "$HOSTNAME$": "prometheus-server",
                },
            ),
            SpecialAgentCommand(
                stdin=(
                    "{'connection': 'prometheus-server', 'protocol': "
                    "'http', 'exporter': [], 'promql_checks': [], "
                    "'host_address': '1.2.3.4', 'host_name': 'host'}"
                ),
                command_arguments=["--disable-cert-verification"],
            ),
            id="minimal configuration",
        ),
        pytest.param(
            {
                "connection": "prometheus-server",
                "verify_cert": True,
                "auth_basic": ("auth_token", {"token": Secret(0)}),
                "protocol": "http",
                "exporter": [("node_exporter", {"entities": ["df", "diskstat", "kernel"]})],
                "promql_checks": [
                    {
                        "service_description": "my-service",
                        "metric_components": [
                            {"metric_label": "my-metric", "promql_query": "my-query"}
                        ],
                    }
                ],
            },
            HostConfig(name="host"),
            SpecialAgentCommand(
                stdin=(
                    "{'connection': 'prometheus-server', 'protocol': "
                    "'http', 'exporter': [('node_exporter', "
                    "{'entities': ['df', 'diskstat', 'kernel']})], "
                    "'promql_checks': [{'service_description': "
                    "'my-service', 'metric_components': "
                    "[{'metric_label': 'my-metric', 'promql_query': "
                    "'my-query'}]}], 'host_address': None, "
                    "'host_name': 'host'}"
                ),
                command_arguments=[
                    "--cert-server-name",
                    "host",
                    "auth_token",
                    "--token",
                    Secret(0),
                ],
            ),
            id="medium configuration",
        ),
        pytest.param(
            {
                "connection": "prometheus-server",
                "verify_cert": True,
                "auth_basic": (
                    "auth_login",
                    {"username": "user", "password": Secret(0)},
                ),
                "protocol": "https",
                "exporter": [
                    (
                        "node_exporter",
                        {"host_mapping": "abc123", "entities": ["df", "diskstat", "kernel"]},
                    ),
                    (
                        "cadvisor",
                        {
                            "entity_level": (
                                "both",
                                {"container_id": "long", "prepend_namespaces": "use_namespace"},
                            ),
                            "namespace_include_patterns": ["p1", "p2"],
                            "entities": ["diskio", "cpu", "df", "interfaces", "memory"],
                        },
                    ),
                ],
                "promql_checks": [
                    {
                        "service_description": "my-service",
                        "metric_components": [
                            {"metric_label": "my-metric", "promql_query": "my-query"}
                        ],
                    },
                    {
                        "service_description": "my-second-service",
                        "host_name": "yet-another-host",
                        "metric_components": [
                            {
                                "metric_label": "l1",
                                "metric_name": "aws_cloudfront_5xx_error_rate",
                                "promql_query": "s.*",
                                "levels": {"lower_levels": ("fixed", (10.0, 20.0))},
                            },
                            {
                                "metric_label": "l2",
                                "promql_query": "t.*",
                                "levels": {
                                    "lower_levels": ("fixed", (0.0, 1.0)),
                                    "upper_levels": ("fixed", (30.0, 40.0)),
                                },
                            },
                        ],
                    },
                ],
            },
            HostConfig(
                name="host",
                ipv4_config=IPv4Config(address="1.2.3.4"),
            ),
            SpecialAgentCommand(
                stdin=(
                    "{'connection': 'prometheus-server', 'protocol': "
                    "'https', 'exporter': [('node_exporter', "
                    "{'host_mapping': 'abc123', 'entities': ['df', "
                    "'diskstat', 'kernel']}), ('cadvisor', "
                    "{'entity_level': ('both', {'container_id': "
                    "'long', 'prepend_namespaces': "
                    "'use_namespace'}), "
                    "'namespace_include_patterns': ['p1', 'p2'], "
                    "'entities': ['diskio', 'cpu', 'df', "
                    "'interfaces', 'memory']})], 'promql_checks': "
                    "[{'service_description': 'my-service', "
                    "'metric_components': [{'metric_label': "
                    "'my-metric', 'promql_query': 'my-query'}]}, "
                    "{'service_description': 'my-second-service', "
                    "'host_name': 'yet-another-host', "
                    "'metric_components': [{'metric_label': 'l1', "
                    "'metric_name': 'aws_cloudfront_5xx_error_rate', "
                    "'promql_query': 's.*', 'levels': "
                    "{'lower_levels': (10.0, 20.0)}}, "
                    "{'metric_label': 'l2', 'promql_query': 't.*', "
                    "'levels': {'lower_levels': (0.0, 1.0), "
                    "'upper_levels': (30.0, 40.0)}}]}], "
                    "'host_address': '1.2.3.4', 'host_name': 'host'}"
                ),
                command_arguments=[
                    "--cert-server-name",
                    "host",
                    "auth_login",
                    "--username",
                    "user",
                    "--password-reference",
                    Secret(0),
                ],
            ),
            id="full configuration",
        ),
    ],
)
def test_command_creation(
    raw_params: Mapping[str, object],
    host_config: HostConfig,
    expected_result: SpecialAgentCommand,
) -> None:
    assert list(
        special_agent_prometheus(
            raw_params,
            host_config,
        )
    ) == [expected_result]
