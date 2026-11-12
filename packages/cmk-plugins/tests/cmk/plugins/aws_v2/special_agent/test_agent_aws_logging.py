#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
"""Only the -v flag decides what the agent logs to stderr."""

import pytest

from cmk.plugins.aws_v2.special_agent.agent_aws_v2 import agent_aws_main, parse_arguments

ARGS = [
    "--hostname",
    "aws-host",
    "--piggyback-naming-convention",
    "ip_region_instance",
    "--region",
    "eu-central-1",
    "--service",
    "ec2",
]


@pytest.fixture(autouse=True)  # ruff: ignore[pytest-fixture-autouse]
def missing_aws_profile(monkeypatch: pytest.MonkeyPatch) -> None:
    """Every run fails, and boto3 logs while it looks for the profile."""
    monkeypatch.setenv("AWS_PROFILE", "doesnotexist")
    monkeypatch.setenv("AWS_EC2_METADATA_DISABLED", "true")


def test_agent_without_verbose_flag_logs_nothing(capsys: pytest.CaptureFixture[str]) -> None:
    agent_aws_main(parse_arguments(ARGS))

    assert capsys.readouterr().err == ""


def test_debug_flag_alone_logs_nothing(capsys: pytest.CaptureFixture[str]) -> None:
    agent_aws_main(parse_arguments([*ARGS, "--debug"]))

    assert capsys.readouterr().err == ""


def test_two_verbose_flags_leave_out_debug_output(capsys: pytest.CaptureFixture[str]) -> None:
    agent_aws_main(parse_arguments([*ARGS, "-vv"]))

    assert "[DEBUG]" not in capsys.readouterr().err


def test_three_verbose_flags_add_debug_output(capsys: pytest.CaptureFixture[str]) -> None:
    agent_aws_main(parse_arguments([*ARGS, "-vvv"]))

    assert "[DEBUG]" in capsys.readouterr().err
