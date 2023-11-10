#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Mapping, Sequence
from typing import Any

import pytest

from cmk.plugins.collection.config_generation.datadog import special_agent_datadog
from cmk.server_side_calls.v1 import HostConfig, HTTPProxy, IPAddressFamily, PlainTextSecret

HOST_CONFIG = HostConfig(
    name="testhost",
    address="0.0.0.1",
    alias="host_alias",
    ip_family=IPAddressFamily.IPv4,
    ipv4address=None,
    ipv6address=None,
    additional_ipv4addresses=[],
    additional_ipv6addresses=[],
)

HTTP_PROXIES = {"my_proxy": HTTPProxy("my_proxy", "My Proxy", "proxy.com")}


@pytest.mark.parametrize(
    "params, expected_result",
    [
        pytest.param(
            {
                "instance": {
                    "api_key": (
                        "password",
                        "12345",
                    ),
                    "app_key": (
                        "password",
                        "powerg",
                    ),
                    "api_host": "api.datadoghq.eu",
                },
                "proxy": (
                    "url",
                    "abc:8567",
                ),
                "monitors": {
                    "tags": [
                        "t1",
                        "t2",
                    ],
                    "monitor_tags": [
                        "mt1",
                        "mt2",
                    ],
                },
                "events": {
                    "max_age": 456,
                    "tags": [
                        "t3",
                        "t4",
                    ],
                    "tags_to_show": [
                        ".*",
                    ],
                    "syslog_facility": 1,
                    "syslog_priority": 1,
                    "service_level": 0,
                    "add_text": True,
                },
                "logs": {
                    "max_age": 456,
                    "query": "test",
                    "indexes": ["t3", "t4"],
                    "text": [("name", "key")],
                    "syslog_facility": 1,
                    "service_level": 0,
                },
            },
            [
                "testhost",
                PlainTextSecret(value="12345", format="%s"),
                PlainTextSecret(value="powerg", format="%s"),
                "api.datadoghq.eu",
                "--proxy",
                "abc:8567",
                "--monitor_tags",
                "t1",
                "t2",
                "--monitor_monitor_tags",
                "mt1",
                "mt2",
                "--event_max_age",
                "456",
                "--event_tags",
                "t3",
                "t4",
                "--event_tags_show",
                ".*",
                "--event_syslog_facility",
                "1",
                "--event_syslog_priority",
                "1",
                "--event_service_level",
                "0",
                "--event_add_text",
                "--log_max_age",
                "456",
                "--log_query",
                "test",
                "--log_indexes",
                "t3",
                "t4",
                "--log_text",
                "name:key",
                "--log_syslog_facility",
                "1",
                "--log_service_level",
                "0",
                "--sections",
                "monitors",
                "events",
                "logs",
            ],
            id="full configuration",
        ),
        pytest.param(
            {
                "instance": {
                    "api_key": (
                        "password",
                        "12345",
                    ),
                    "app_key": (
                        "password",
                        "powerg",
                    ),
                    "api_host": "api.datadoghq.eu",
                },
                "monitors": {},
                "events": {
                    "max_age": 600,
                    "syslog_facility": 1,
                    "syslog_priority": 1,
                    "service_level": 0,
                    "add_text": False,
                },
            },
            [
                "testhost",
                PlainTextSecret(value="12345", format="%s"),
                PlainTextSecret(value="powerg", format="%s"),
                "api.datadoghq.eu",
                "--monitor_tags",
                "--monitor_monitor_tags",
                "--event_max_age",
                "600",
                "--event_tags",
                "--event_tags_show",
                "--event_syslog_facility",
                "1",
                "--event_syslog_priority",
                "1",
                "--event_service_level",
                "0",
                "--sections",
                "monitors",
                "events",
            ],
            id="first setup",
        ),
        pytest.param(
            {
                "instance": {
                    "api_key": (
                        "password",
                        "12345",
                    ),
                    "app_key": (
                        "password",
                        "powerg",
                    ),
                    "api_host": "api.datadoghq.eu",
                },
            },
            [
                "testhost",
                PlainTextSecret(value="12345", format="%s"),
                PlainTextSecret(value="powerg", format="%s"),
                "api.datadoghq.eu",
                "--sections",
            ],
            id="minimal case",
        ),
    ],
)
def test_datadog_argument_parsing(
    params: Mapping[str, Any],
    expected_result: Sequence[str],
) -> None:
    parsed_params = special_agent_datadog.parameter_parser(params)
    commands = list(
        special_agent_datadog.commands_function(parsed_params, HOST_CONFIG, HTTP_PROXIES)
    )

    assert len(commands) == 1
    assert commands[0].command_arguments == expected_result
