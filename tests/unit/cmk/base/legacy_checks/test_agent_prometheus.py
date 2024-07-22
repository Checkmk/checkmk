#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Mapping, Sequence

import pytest

from cmk.base.legacy_checks.agent_prometheus import agent_prometheus_arguments


@pytest.mark.parametrize(
    ["params", "hostname", "ip_address", "expected_result"],
    [
        pytest.param(
            {
                "connection": "prometheus-server",
                "verify-cert": False,
                "protocol": "http",
                "exporter": [],
                "promql_checks": [],
            },
            "host",
            None,
            [
                "--config",
                "{'connection': 'prometheus-server', 'verify-cert': False, 'protocol': "
                "'http', 'exporter': [], 'promql_checks': [], 'host_address': None, "
                "'host_name': 'host'}",
            ],
            id="minimal configuration",
        ),
        pytest.param(
            {
                "connection": "prometheus-server",
                "verify-cert": True,
                "auth_basic": ("auth_token", {"token": ("password", "token")}),
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
            "host",
            "1.2.3.4",
            [
                "--config",
                "{'connection': 'prometheus-server', 'verify-cert': True, 'protocol': "
                "'http', 'exporter': [('node_exporter', {'entities': ['df', 'diskstat', "
                "'kernel']})], 'promql_checks': [{'service_description': 'my-service', "
                "'metric_components': [{'metric_label': 'my-metric', 'promql_query': "
                "'my-query'}]}], 'host_address': '1.2.3.4', 'host_name': 'host'}",
                "auth_token",
                "--token",
                "token",
            ],
            id="medium configuration",
        ),
        pytest.param(
            {
                "connection": "prometheus-server",
                "verify-cert": True,
                "auth_basic": (
                    "auth_login",
                    {"username": "user", "password": ("password", "password")},
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
                            "entities": ["diskio", "cpu", "df", "if", "memory"],
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
                                "levels": {"lower_levels": (10.0, 20.0)},
                            },
                            {
                                "metric_label": "l2",
                                "promql_query": "t.*",
                                "levels": {
                                    "lower_levels": (0.0, 1.0),
                                    "upper_levels": (30.0, 40.0),
                                },
                            },
                        ],
                    },
                ],
            },
            "host",
            "1.2.3.4",
            [
                "--config",
                "{'connection': 'prometheus-server', 'verify-cert': True, 'protocol': "
                "'https', 'exporter': [('node_exporter', {'host_mapping': 'abc123', "
                "'entities': ['df', 'diskstat', 'kernel']}), ('cadvisor', {'entity_level': "
                "('both', {'container_id': 'long', 'prepend_namespaces': "
                "'use_namespace'}), 'namespace_include_patterns': ['p1', 'p2'], "
                "'entities': ['diskio', 'cpu', 'df', 'if', 'memory']})], 'promql_checks': "
                "[{'service_description': 'my-service', 'metric_components': "
                "[{'metric_label': 'my-metric', 'promql_query': 'my-query'}]}, "
                "{'service_description': 'my-second-service', 'host_name': "
                "'yet-another-host', 'metric_components': [{'metric_label': 'l1', "
                "'metric_name': 'aws_cloudfront_5xx_error_rate', 'promql_query': 's.*', "
                "'levels': {'lower_levels': (10.0, 20.0)}}, {'metric_label': 'l2', "
                "'promql_query': 't.*', 'levels': {'lower_levels': (0.0, 1.0), "
                "'upper_levels': (30.0, 40.0)}}]}], 'host_address': '1.2.3.4', "
                "'host_name': 'host'}",
                "auth_login",
                "--username",
                "user",
                "--password-reference",
                "password",
            ],
            id="full configuration",
        ),
    ],
)
def test_command_creation(
    params: Mapping[str, object],
    hostname: str,
    ip_address: str | None,
    expected_result: Sequence[object],
) -> None:
    assert (
        agent_prometheus_arguments(
            params,
            hostname,
            ip_address,
        )
        == expected_result
    )
