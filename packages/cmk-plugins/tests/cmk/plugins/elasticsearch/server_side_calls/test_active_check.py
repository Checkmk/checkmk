#!/usr/bin/env python3
# Copyright (C) 2023 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Mapping, Sequence

import pytest

from cmk.plugins.elasticsearch.server_side_calls.active_check import active_check_config as config
from cmk.server_side_calls.v1 import HostConfig, IPv4Config


@pytest.mark.parametrize(
    "params,host_config,expected_args,expected_description",
    [
        pytest.param(
            {
                "svc_item": "stuff",
                "index": ["f", "o", "o"],
                "pattern": "bar",
                "timerange": 1,
                "verify_tls_cert": True,
            },
            HostConfig(name="test", ipv4_config=IPv4Config(address="test")),
            ["-q", "bar", "-t", "1", "-i", "f o o", "-H", "test"],
            "Elasticsearch Query stuff",
            id="basic config",
        ),
        pytest.param(
            {"svc_item": "stuff", "pattern": "bar", "timerange": 1, "verify_tls_cert": False},
            HostConfig(name="test", ipv4_config=IPv4Config(address="test")),
            ["-q", "bar", "-t", "1", "-H", "test", "--no-verify-tls-cert"],
            "Elasticsearch Query stuff",
            id="basic config without TLS verification",
        ),
        pytest.param(
            {
                "svc_item": "stuff",
                "index": ["f", "o", "o"],
                "pattern": "bar",
                "timerange": 1,
                "verify_tls_cert": True,
                "upper_log_count_thresholds": ("fixed", (1, 5)),
                "lower_log_count_thresholds": ("fixed", (1, 0)),
            },
            HostConfig(name="test", ipv4_config=IPv4Config(address="test")),
            [
                "-q",
                "bar",
                "-t",
                "1",
                "-i",
                "f o o",
                "--warn-upper-log-count=1",
                "--crit-upper-log-count=5",
                "--warn-lower-log-count=1",
                "--crit-lower-log-count=0",
                "-H",
                "test",
            ],
            "Elasticsearch Query stuff",
            id="config with count",
        ),
    ],
)
def test_check_elasticsearch_query(
    params: Mapping[str, object],
    host_config: HostConfig,
    expected_args: Sequence[str],
    expected_description: str,
) -> None:
    # Act
    commands = list(config(params, host_config))
    # Assert
    assert len(commands) == 1
    assert commands[0].service_description == expected_description
    assert commands[0].command_arguments == expected_args
