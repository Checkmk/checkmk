#!/usr/bin/env python3
# Copyright (C) 2023 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.plugins.gcp.server_side_calls.gcp_status import special_agent_gcp_status
from cmk.server_side_calls.v1 import HostConfig, SpecialAgentCommand


def test_command_creation() -> None:
    assert list(
        special_agent_gcp_status(
            {"regions": ["asia_east1"]},
            HostConfig(name="hostname"),
        )
    ) == [SpecialAgentCommand(command_arguments=["asia-east1"])]
