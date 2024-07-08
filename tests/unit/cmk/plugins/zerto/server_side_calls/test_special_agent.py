#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Mapping, Sequence

import pytest

from cmk.plugins.zerto.server_side_calls.special_agent import commands_function, Params
from cmk.server_side_calls.v1 import HostConfig, IPv4Config, Secret, SpecialAgentCommand


@pytest.mark.parametrize(
    ["params", "expected_args"],
    [
        pytest.param(
            {"username": "usr", "password": Secret(id=1, pass_safely=True)},
            [
                "--authentication",
                "windows",
                "-u",
                "usr",
                "-p",
                Secret(id=1, pass_safely=False),
                "address",
            ],
        ),
    ],
)
def test_zerto(params: Mapping[str, object], expected_args: Sequence[str]) -> None:
    assert list(
        commands_function(
            Params.model_validate(params),
            HostConfig(name="testhost", ipv4_config=IPv4Config(address="address")),
        )
    ) == [
        SpecialAgentCommand(command_arguments=expected_args),
    ]
