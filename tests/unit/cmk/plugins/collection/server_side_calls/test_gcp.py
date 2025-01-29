#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Mapping, Sequence
from typing import Any

import pytest
import time_machine

from cmk.plugins.gcp.server_side_calls.gcp import special_agent_gcp
from cmk.server_side_calls.v1 import HostConfig, IPv4Config, Secret

HOST_CONFIG = HostConfig(
    name="hostname",
    ipv4_config=IPv4Config(address="0.0.0.1"),
)


@time_machine.travel("2022-01-12")
@pytest.mark.parametrize(
    "params, expected_result",
    [
        pytest.param(
            {
                "project": "test",
                "credentials": Secret(0),
                "services": ["gcs", "run"],
            },
            [
                "--project",
                "test",
                "--credentials",
                Secret(0).unsafe(),
                "--date",
                "2022-01-12",
                "--services",
                "gcs",
                "run",
                "--piggy-back-prefix",
                "test",
            ],
            id="minimal case",
        ),
        pytest.param(
            {
                "project": "test",
                "credentials": Secret(0),
                "cost": {"tableid": "checkmk"},
                "services": [],
            },
            [
                "--project",
                "test",
                "--credentials",
                Secret(0).unsafe(),
                "--date",
                "2022-01-12",
                "--cost_table",
                "checkmk",
                "--piggy-back-prefix",
                "test",
            ],
            id="cost monitoring only",
        ),
        pytest.param(
            {
                "project": "test",
                "credentials": Secret(0),
                "cost": {"tableid": "checkmk"},
                "services": ["gcs"],
            },
            [
                "--project",
                "test",
                "--credentials",
                Secret(0).unsafe(),
                "--date",
                "2022-01-12",
                "--cost_table",
                "checkmk",
                "--services",
                "gcs",
                "--piggy-back-prefix",
                "test",
            ],
            id="cost monitoring and checks",
        ),
        pytest.param(
            {
                "project": "test",
                "credentials": Secret(2),
                "services": [],
                "piggyback": {"prefix": "custom-prefix", "piggyback_services": ["gce"]},
            },
            [
                "--project",
                "test",
                "--credentials",
                Secret(2).unsafe(),
                "--date",
                "2022-01-12",
                "--services",
                "gce",
                "--piggy-back-prefix",
                "custom-prefix",
            ],
            id="piggyback prefix and services",
        ),
    ],
)
def test_gcp_argument_parsing(
    params: Mapping[str, Any],
    expected_result: Sequence[str],
) -> None:
    commands = list(special_agent_gcp(params, HOST_CONFIG))
    assert commands[0].command_arguments == expected_result
