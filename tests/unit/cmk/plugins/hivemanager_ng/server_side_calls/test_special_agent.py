#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.plugins.hivemanager_ng.server_side_calls.special_agent import special_agent_hivemanager_ng
from cmk.server_side_calls.v1 import HostConfig, Secret, SpecialAgentCommand


def test_command_creation() -> None:
    assert list(
        special_agent_hivemanager_ng(
            {
                "url": "http://cloud.com",
                "vhm_id": "102",
                "api_token": "token",
                "client_id": "clientID",
                "client_secret": Secret(1),
                "redirect_url": "http://redirect.com",
            },
            HostConfig(name="hostname"),
        )
    ) == [
        SpecialAgentCommand(
            command_arguments=[
                "http://cloud.com",
                "102",
                "token",
                "clientID",
                Secret(id=1, format="%s", pass_safely=False),
                "http://redirect.com",
            ]
        )
    ]
