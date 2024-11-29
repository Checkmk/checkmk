#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Mapping, Sequence

import pytest

from cmk.plugins.collection.server_side_calls.cmk_inv import CmkInvParams, generate_cmk_inv_commands
from cmk.server_side_calls.v1 import HostConfig, IPv4Config

ARGS = [
    "--inv-fail-status=1",
    "--hw-changes=0",
    "--sw-changes=0",
    "--sw-missing=0",
    "--nw-changes=0",
    "unittest_name",
]


@pytest.mark.parametrize(
    "params,expected_args",
    [
        (None, ARGS),
        ({}, ARGS),
        ({"timeout": 0}, ARGS),
    ],
)
def test_check_cmk_inv_argument_parsing(
    params: None | Mapping[str, object], expected_args: Sequence[str]
) -> None:
    """Tests if all required arguments are present."""
    commands = list(
        generate_cmk_inv_commands(
            CmkInvParams.model_validate(params),
            HostConfig(
                name="unittest_name",
                ipv4_config=IPv4Config(address="unittest_address"),
            ),
        )
    )
    assert len(commands) == 1
    assert commands[0].command_arguments == expected_args
