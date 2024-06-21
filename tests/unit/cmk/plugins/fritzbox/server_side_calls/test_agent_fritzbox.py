#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Mapping

import pytest

from cmk.plugins.fritzbox.server_side_calls.agent_call import special_agent_fritzbox
from cmk.server_side_calls.v1 import HostConfig, IPv4Config, SpecialAgentCommand

HOST_CONFIG = HostConfig(
    name="my_host",
    ipv4_config=IPv4Config(address="resolved_address"),
)


@pytest.mark.parametrize(
    "params,expected",
    [
        (
            {},
            (SpecialAgentCommand(command_arguments=("resolved_address",)),),
        ),
        (
            {
                "timeout": 10,
            },
            (
                SpecialAgentCommand(
                    command_arguments=("--timeout", "10", "resolved_address"),
                ),
            ),
        ),
    ],
)
def test_fritzbox_argument_parsing(
    params: Mapping[str, object], expected: tuple[SpecialAgentCommand]
) -> None:
    """Tests if all required arguments are present."""
    assert tuple(special_agent_fritzbox(params, HOST_CONFIG)) == expected
