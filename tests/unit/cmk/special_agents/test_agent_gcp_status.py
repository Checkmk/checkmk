#!/usr/bin/env python3
# Copyright (C) 2023 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import json

import pytest

from cmk.special_agents import agent_gcp_status


def test_health_serialization(capsys: pytest.CaptureFixture[str]) -> None:
    # Assemble
    def _health_info() -> str:
        return '{"fake": "test"}'

    args = agent_gcp_status.parse_arguments([])
    # Act
    agent_gcp_status.write_section(args, health_info=_health_info)
    captured = capsys.readouterr()
    lines = captured.out.rstrip().split("\n")
    # Assert
    assert lines[0] == "<<<gcp_health:sep(0)>>>"
    assert json.loads(lines[1]) == {"fake": "test"}
    assert len(lines) == 2
