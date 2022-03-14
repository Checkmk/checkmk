#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from typing import Any, Mapping, Sequence

import pytest

from tests.testlib import SpecialAgent

pytestmark = pytest.mark.checks


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
            },
            [
                "testhost",
                "12345",
                "powerg",
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
                "--sections",
                "monitors",
                "events",
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
                "12345",
                "powerg",
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
                "12345",
                "powerg",
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
    assert (
        SpecialAgent("agent_datadog").argument_func(
            params,
            "testhost",
            "address",
        )
        == expected_result
    )
