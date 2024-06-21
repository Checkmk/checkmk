#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
from collections.abc import Mapping, Sequence
from typing import Any

import pytest

from .checktestlib import SpecialAgent


@pytest.mark.parametrize(
    ["params", "expected_args"],
    [
        pytest.param(
            {
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
                "vurystrong",
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
                "subscription": "banana",
                "tenant": "strawberry",
                "client": "blueberry",
                "secret": ("store", "azure"),
                "config": {
                    "explicit": [{"group_name": "my_res_group"}],
                    "tag_based": [("my_tag", "exists")],
                },
            },
            [
                "--tenant",
                "strawberry",
                "--client",
                "blueberry",
                "--secret",
                ("store", "azure", "%s"),
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
                "subscription": "banana",
                "tenant": "strawberry",
                "client": "blueberry",
                "secret": ("store", "azure"),
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
                ("store", "azure", "%s"),
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
    agent = SpecialAgent("agent_azure")
    arguments = agent.argument_func(params, "testhost", "address")
    assert arguments == expected_args
