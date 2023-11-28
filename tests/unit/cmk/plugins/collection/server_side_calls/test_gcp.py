#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Mapping, Sequence
from typing import Any

import pytest
from freezegun import freeze_time

from cmk.plugins.collection.server_side_calls.gcp import special_agent_gcp
from cmk.server_side_calls.v1 import HostConfig, IPAddressFamily, PlainTextSecret, StoredSecret

pytestmark = pytest.mark.checks

HOST_CONFIG = HostConfig(
    name="hostname",
    address="0.0.0.1",
    alias="host_alias",
    ip_family=IPAddressFamily.IPV4,
)


@freeze_time("2022-01-12")
@pytest.mark.parametrize(
    "params, expected_result",
    [
        pytest.param(
            {
                "project": "test",
                "credentials": ("password", "a_very_important_secret"),
                "services": ["gcs", "run"],
            },
            [
                "--project",
                "test",
                "--credentials",
                PlainTextSecret(value="a_very_important_secret", format="%s"),
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
                "credentials": ("password", "a_very_important_secret"),
                "cost": {"tableid": "checkmk"},
                "services": [],
            },
            [
                "--project",
                "test",
                "--credentials",
                PlainTextSecret(value="a_very_important_secret", format="%s"),
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
                "credentials": ("store", "password_id_1"),
                "cost": {"tableid": "checkmk"},
                "services": ["gcs"],
            },
            [
                "--project",
                "test",
                "--credentials",
                StoredSecret(value="password_id_1", format="%s"),
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
                "credentials": ("store", "password_id_2"),
                "services": [],
                "piggyback": {"prefix": "custom-prefix", "piggyback_services": ["gce"]},
            },
            [
                "--project",
                "test",
                "--credentials",
                StoredSecret(value="password_id_2", format="%s"),
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
    parsed_params = special_agent_gcp.parameter_parser(params)
    commands = list(special_agent_gcp.commands_function(parsed_params, HOST_CONFIG, {}))
    assert commands[0].command_arguments == expected_result
