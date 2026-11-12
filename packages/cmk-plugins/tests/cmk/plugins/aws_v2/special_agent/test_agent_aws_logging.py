#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
"""Only the -v flag decides what the agent logs, and only failures are warnings."""

import logging
from collections.abc import Iterator

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
def _restore_root_logger() -> Iterator[None]:
    """The agent replaces the root handler with one bound to this test's stderr."""
    root = logging.getLogger()
    handlers = root.handlers[:]
    level = root.level
    yield
    root.handlers[:] = handlers
    root.setLevel(level)


@pytest.fixture(name="missing_aws_profile")
def _missing_aws_profile(monkeypatch: pytest.MonkeyPatch) -> None:
    """Every agent run fails, and boto3 logs while it looks for the profile."""
    monkeypatch.setenv("AWS_PROFILE", "doesnotexist")
    monkeypatch.setenv("AWS_EC2_METADATA_DISABLED", "true")


@pytest.mark.usefixtures("missing_aws_profile")
def test_agent_without_verbose_flag_logs_nothing(capsys: pytest.CaptureFixture[str]) -> None:
    agent_aws_main(parse_arguments(ARGS))

    assert capsys.readouterr().err == ""


@pytest.mark.usefixtures("missing_aws_profile")
def test_debug_flag_alone_logs_nothing(capsys: pytest.CaptureFixture[str]) -> None:
    agent_aws_main(parse_arguments([*ARGS, "--debug"]))

    assert capsys.readouterr().err == ""


@pytest.mark.usefixtures("missing_aws_profile")
def test_one_verbose_flag_logs_the_access_failure(capsys: pytest.CaptureFixture[str]) -> None:
    agent_aws_main(parse_arguments([*ARGS, "-v"]))

    assert "[WARNING] Cannot list the accounts to monitor" in capsys.readouterr().err


@pytest.mark.usefixtures("missing_aws_profile")
def test_two_verbose_flags_leave_out_debug_output(capsys: pytest.CaptureFixture[str]) -> None:
    agent_aws_main(parse_arguments([*ARGS, "-vv"]))

    assert "[DEBUG]" not in capsys.readouterr().err


@pytest.mark.usefixtures("missing_aws_profile")
def test_three_verbose_flags_add_debug_output(capsys: pytest.CaptureFixture[str]) -> None:
    agent_aws_main(parse_arguments([*ARGS, "-vvv"]))

    assert "[DEBUG]" in capsys.readouterr().err
