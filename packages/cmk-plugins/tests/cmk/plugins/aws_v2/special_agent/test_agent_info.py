#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import pytest

from cmk.plugins.aws_v2.special_agent.agent_info import AgentInfoRow, write_agent_info


def test_agent_info_writes_one_json_line_per_row(capsys: pytest.CaptureFixture[str]) -> None:
    write_agent_info(
        [
            AgentInfoRow("ok", "333333333333"),
            AgentInfoRow("error", "444444444444", "Access denied"),
            AgentInfoRow("error", reason="No AWS credentials found."),
        ]
    )

    assert capsys.readouterr().out.splitlines() == [
        "<<<aws_v2_agent_info:sep(0)>>>",
        '{"status": "ok", "account": "333333333333"}',
        '{"status": "error", "account": "444444444444", "reason": "Access denied"}',
        '{"status": "error", "reason": "No AWS credentials found."}',
    ]


def test_agent_info_without_rows_still_writes_the_section(
    capsys: pytest.CaptureFixture[str],
) -> None:
    write_agent_info([])

    assert capsys.readouterr().out == "<<<aws_v2_agent_info:sep(0)>>>\n"
