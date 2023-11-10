#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Mapping, Sequence
from typing import Any

import pytest

from cmk.plugins.collection.config_generation.azure import special_agent_azure
from cmk.server_side_calls.v1 import HostConfig, IPAddressFamily, PlainTextSecret, StoredSecret

HOST_CONFIG = HostConfig(
    name="host",
    address="127.0.0.1",
    alias="host_alias",
    ip_family=IPAddressFamily.IPv4,
)


@pytest.mark.parametrize(
    ["params", "expected_args"],
    [
        pytest.param(
            {
                "authority": "china",
                "subscription": "banana",
                "tenant": "strawberry",
                "client": "blueberry",
                "secret": ("password", "vurystrong"),
                "config": {},
                "services": ["users_count", "Microsoft.DBforMySQL/servers"],
            },
            [
                "--tenant",
                "strawberry",
                "--client",
                "blueberry",
                "--secret",
                PlainTextSecret(value="vurystrong", format="%s"),
                "--authority",
                "china",
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
                "authority": "global",
                "subscription": "banana",
                "tenant": "strawberry",
                "client": "blueberry",
                "secret": ("store", "azure"),
                "config": {
                    "explicit": [{"group_name": "my_res_group"}],
                    "tag_based": [("my_tag", "exists")],
                },
                "services": [],
            },
            [
                "--tenant",
                "strawberry",
                "--client",
                "blueberry",
                "--secret",
                StoredSecret(value="azure", format="%s"),
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
                "authority": "global",
                "subscription": "banana",
                "tenant": "strawberry",
                "client": "blueberry",
                "secret": ("store", "azure"),
                "services": [],
                "config": {
                    "explicit": [{"group_name": "my_res_group", "resources": ["res1", "res2"]}],
                    "tag_based": [("my_tag_1", "exists"), ("my_tag_2", ("value", "t1"))],
                },
                "sequential": True,
                "proxy": ("environment", "environment"),
            },
            [
                "--tenant",
                "strawberry",
                "--client",
                "blueberry",
                "--secret",
                StoredSecret(value="azure", format="%s"),
                "--authority",
                "global",
                "--subscription",
                "banana",
                "--sequential",
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
    parsed_params = special_agent_azure.parameter_parser(params)
    commands = list(special_agent_azure.commands_function(parsed_params, HOST_CONFIG, {}))

    assert len(commands) == 1
    assert commands[0].command_arguments == expected_args
