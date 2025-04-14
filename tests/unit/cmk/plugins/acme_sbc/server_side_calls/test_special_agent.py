#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.plugins.acme.server_side_calls.special_agent import special_agent_acme_sbc
from cmk.server_side_calls.v1 import HostConfig, SpecialAgentCommand


def test_command_creation() -> None:
    assert list(
        special_agent_acme_sbc(
            {},
            HostConfig(name="hostname"),
        )
    ) == [SpecialAgentCommand(command_arguments=["hostname"])]
