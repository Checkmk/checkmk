#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Mapping

import pytest

from cmk.plugins.salesforce.server_side_calls.special_agent import special_agent_salesforce
from cmk.server_side_calls.v1 import HostConfig, IPv4Config, SpecialAgentCommand

HOST_CONFIG = HostConfig(
    name="hostname",
    ipv4_config=IPv4Config(address="address"),
)


@pytest.mark.parametrize(
    "raw_params,expected_command",
    [
        pytest.param(
            {"instances": ["5"]},
            SpecialAgentCommand(
                command_arguments=[
                    "--section_url",
                    "salesforce_instances,https://api.status.salesforce.com/v1/instances/5/status",
                ]
            ),
            id="single instance",
        ),
        pytest.param(
            {"instances": ["foo", "bar"]},
            SpecialAgentCommand(
                command_arguments=[
                    "--section_url",
                    "salesforce_instances,https://api.status.salesforce.com/v1/instances/foo/status",
                    "--section_url",
                    "salesforce_instances,https://api.status.salesforce.com/v1/instances/bar/status",
                ]
            ),
            id="multiple instances",
        ),
    ],
)
def test_special_agent_salesforce_command_creation(
    raw_params: Mapping[str, object],
    expected_command: SpecialAgentCommand,
) -> None:
    assert list(special_agent_salesforce(raw_params, HOST_CONFIG)) == [expected_command]
