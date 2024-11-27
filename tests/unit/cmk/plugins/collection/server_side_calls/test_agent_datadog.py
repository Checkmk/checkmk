#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Mapping, Sequence
from typing import Any

import pytest

from cmk.plugins.datadog.server_side_calls.agent_datadog import special_agent_datadog
from cmk.server_side_calls.v1 import HostConfig, IPv4Config, Secret, URLProxy


@pytest.mark.parametrize(
    "params, expected_result",
    [
        pytest.param(
            {
                "instance": {
                    "api_key": Secret(1),
                    "app_key": Secret(2),
                    "api_host": "api.datadoghq.eu",
                },
                "proxy": URLProxy(url="abc:8567"),
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
                    "syslog_facility": ("user", 1),
                    "syslog_priority": ("alert", 1),
                    "service_level": ("(no Service level)", 0),
                    "add_text": "add_text",
                },
                "logs": {
                    "max_age": 456,
                    "query": "test",
                    "indexes": ["t3", "t4"],
                    "text": [{"name": "name", "key": "key"}],
                    "syslog_facility": ("user", 1),
                    "service_level": ("(no Service level)", 0),
                },
            },
            [
                "testhost",
                Secret(1).unsafe(),
                Secret(2).unsafe(),
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
                    "api_key": Secret(3),
                    "app_key": Secret(4),
                    "api_host": "api.datadoghq.eu",
                },
                "monitors": {},
                "events": {
                    "max_age": 600,
                    "syslog_facility": ("user", 1),
                    "syslog_priority": ("alert", 1),
                    "service_level": ("(no Service level)", 0),
                    "add_text": "do_not_add_text",
                },
            },
            [
                "testhost",
                Secret(3).unsafe(),
                Secret(4).unsafe(),
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
                    "api_key": Secret(5),
                    "app_key": Secret(6),
                    "api_host": "api.datadoghq.eu",
                },
            },
            [
                "testhost",
                Secret(5).unsafe(),
                Secret(6).unsafe(),
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
    commands = list(
        special_agent_datadog(
            params,
            HostConfig(
                name="testhost",
                ipv4_config=IPv4Config(address="0.0.0.1"),
            ),
        )
    )
    assert commands[0].command_arguments == expected_result
