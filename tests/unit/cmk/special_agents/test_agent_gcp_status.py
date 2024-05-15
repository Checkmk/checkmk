#!/usr/bin/env python3
# Copyright (C) 2023 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import pytest

from cmk.plugins.gcp.special_agents import agent_gcp_status


def test_health_serialization(capsys: pytest.CaptureFixture[str]) -> None:
    # Assemble
    def _health_info() -> str:
        return '{"fake": "test"}'

    args = agent_gcp_status.parse_arguments(["Regions"])
    discovery_param = agent_gcp_status.DiscoveryParam.model_validate(vars(args))
    output = agent_gcp_status.AgentOutput(
        discovery_param=discovery_param,
        health_info=_health_info(),
    )
    # Act
    agent_gcp_status.write_section(args, health_info=_health_info)
    captured = capsys.readouterr()
    lines = captured.out.rstrip().split("\n")
    # Assert
    assert lines[0] == "<<<gcp_status:sep(0)>>>"
    assert lines[1] == output.model_dump_json()
    assert len(lines) == 2
