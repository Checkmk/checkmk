#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Mapping

import pytest

from cmk.plugins.jira.server_side_calls.special_agent import special_agent_jira
from cmk.server_side_calls.v1 import HostConfig, IPv4Config, SpecialAgentCommand
from cmk.server_side_calls.v1._utils import Secret

HOST_CONFIG = HostConfig(
    name="testhost",
    ipv4_config=IPv4Config(address="1.2.3.4"),
)


@pytest.mark.parametrize(
    "raw_params, expected_command",
    [
        pytest.param(
            {
                "user": "username",
                "password": Secret(23),
                "instance": "test",
                "protocol": "https",
            },
            SpecialAgentCommand(
                command_arguments=[
                    "-P",
                    "https",
                    "-u",
                    "username",
                    "-s",
                    Secret(23).unsafe(),
                    "--hostname",
                    "test",
                ]
            ),
            id="with instance",
        ),
        pytest.param(
            {
                "user": "username",
                "password": Secret(23),
                "protocol": "https",
            },
            SpecialAgentCommand(
                command_arguments=[
                    "-P",
                    "https",
                    "-u",
                    "username",
                    "-s",
                    Secret(23).unsafe(),
                    "--hostname",
                    "testhost",
                ]
            ),
            id="without instance",
        ),
        pytest.param(
            {
                "user": "username",
                "password": Secret(23),
                "protocol": "https",
                "project_workflows": [
                    {"project": "project1", "workflows": ["workflow1", "workflow2"]},
                ],
            },
            SpecialAgentCommand(
                command_arguments=[
                    "-P",
                    "https",
                    "-u",
                    "username",
                    "-s",
                    Secret(23).unsafe(),
                    "--project-workflows-key",
                    "project1",
                    "--project-workflows-values",
                    "workflow1",
                    "workflow2",
                    "--hostname",
                    "testhost",
                ]
            ),
            id="with project_workflows",
        ),
        pytest.param(
            {
                "user": "username",
                "password": Secret(23),
                "protocol": "https",
                "jql": [
                    {
                        "service_description": "My averaged field",
                        "result": ("average", {"field_name": "customfield_1001", "limit": 1000}),
                        "query": "project = my_project and status = open",
                    },
                ],
            },
            SpecialAgentCommand(
                command_arguments=[
                    "-P",
                    "https",
                    "-u",
                    "username",
                    "-s",
                    Secret(23).unsafe(),
                    "--jql-desc",
                    "My averaged field",
                    "--jql-query",
                    "project = my_project and status = open",
                    "--jql-result",
                    "average",
                    "--jql-field",
                    "customfield_1001",
                    "--jql-limit",
                    "1000",
                    "--hostname",
                    "testhost",
                ]
            ),
            id="with jql average",
        ),
        pytest.param(
            {
                "user": "username",
                "password": Secret(23),
                "protocol": "https",
                "jql": [
                    {
                        "service_description": "My counted field",
                        "result": ("count", "count"),
                        "query": 'project = my_project and status = "waiting for something"',
                    },
                ],
            },
            SpecialAgentCommand(
                command_arguments=[
                    "-P",
                    "https",
                    "-u",
                    "username",
                    "-s",
                    Secret(23).unsafe(),
                    "--jql-desc",
                    "My counted field",
                    "--jql-query",
                    'project = my_project and status = "waiting for something"',
                    "--jql-result",
                    "count",
                    "--jql-field",
                    "None",
                    "--jql-limit",
                    "0",
                    "--hostname",
                    "testhost",
                ]
            ),
            id="with jql count",
        ),
        pytest.param(
            {
                "user": "username",
                "password": Secret(23),
                "protocol": "https",
                "jql": [
                    {
                        "service_description": "My summed up field",
                        "result": ("sum", {"field_name": "customfield_1000", "limit": 1000}),
                        "query": "project = my_project and status = closed",
                    },
                ],
            },
            SpecialAgentCommand(
                command_arguments=[
                    "-P",
                    "https",
                    "-u",
                    "username",
                    "-s",
                    Secret(23).unsafe(),
                    "--jql-desc",
                    "My summed up field",
                    "--jql-query",
                    "project = my_project and status = closed",
                    "--jql-result",
                    "sum",
                    "--jql-field",
                    "customfield_1000",
                    "--jql-limit",
                    "1000",
                    "--hostname",
                    "testhost",
                ]
            ),
            id="with jql sum",
        ),
    ],
)
def test_special_agent_jira_command_creation(
    raw_params: Mapping[str, object],
    expected_command: SpecialAgentCommand,
) -> None:
    assert list(special_agent_jira(raw_params, HOST_CONFIG)) == [expected_command]
