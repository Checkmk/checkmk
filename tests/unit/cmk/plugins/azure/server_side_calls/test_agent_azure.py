#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Mapping, Sequence
from typing import Any

import pytest

from cmk.plugins.azure.server_side_calls.agent_azure import (
    agent_azure_arguments as commands_function,
)
from cmk.plugins.azure.server_side_calls.agent_azure import AzureParams
from cmk.server_side_calls.v1 import EnvProxy, HostConfig, Secret


@pytest.mark.parametrize(
    ["params", "expected_args"],
    [
        pytest.param(
            {
                "authority": "global_",
                "subscription": "banana",
                "tenant": "strawberry",
                "client": "blueberry",
                "secret": Secret(0),
                "config": {},
                "services": ["users_count", "Microsoft_DBforMySQL_slash_servers"],
            },
            [
                "--tenant",
                "strawberry",
                "--client",
                "blueberry",
                "--secret",
                Secret(0).unsafe(),
                "--authority",
                "global",
                "--subscription",
                "banana",
                "--services",
                "users_count",
                "Microsoft.DBforMySQL/servers",
            ],
            id="explicit_password",
        ),
        pytest.param(
            {
                "authority": "global_",
                "subscription": "banana",
                "tenant": "strawberry",
                "client": "blueberry",
                "secret": Secret(0),
                "config": {
                    "explicit": [{"group_name": "my_res_group"}],
                    "tag_based": [{"tag": "my_tag", "condition": ("exists", None)}],
                },
                "services": [],
            },
            [
                "--tenant",
                "strawberry",
                "--client",
                "blueberry",
                "--secret",
                Secret(0).unsafe(),
                "--authority",
                "global",
                "--subscription",
                "banana",
                "--explicit-config",
                "group=my_res_group",
                "--require-tag",
                "my_tag",
            ],
            id="password_from_store",
        ),
        pytest.param(
            {
                "authority": "global_",
                "subscription": "banana",
                "tenant": "strawberry",
                "client": "blueberry",
                "secret": Secret(0),
                "config": {
                    "explicit": [{"group_name": "my_res_group", "resources": ["res1", "res2"]}],
                    "tag_based": [
                        {"tag": "my_tag_1", "condition": ("exists", None)},
                        {"tag": "my_tag_2", "condition": ("equals", "t1")},
                    ],
                },
                "proxy": EnvProxy(),
                "services": [],
            },
            [
                "--tenant",
                "strawberry",
                "--client",
                "blueberry",
                "--secret",
                Secret(0).unsafe(),
                "--authority",
                "global",
                "--subscription",
                "banana",
                "--proxy",
                "FROM_ENVIRONMENT",
                "--explicit-config",
                "group=my_res_group",
                "resources=res1,res2",
                "--require-tag",
                "my_tag_1",
                "--require-tag-value",
                "my_tag_2",
                "t1",
            ],
            id="all_arguments",
        ),
    ],
)
def test_azure_argument_parsing(
    params: Mapping[str, Any],
    expected_args: Sequence[Any],
) -> None:
    """Tests if all required arguments are present."""
    host_config = HostConfig(name="test")
    commands = list(commands_function(AzureParams.model_validate(params), host_config))
    assert len(commands) == 1
    arguments = commands[0].command_arguments
    assert arguments == expected_args
