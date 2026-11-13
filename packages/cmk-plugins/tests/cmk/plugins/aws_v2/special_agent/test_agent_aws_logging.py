#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
"""Only the -v flag decides what the agent logs, and only failures are warnings."""

import io
import logging
from argparse import Namespace as Args
from collections.abc import Iterator
from unittest import mock

import pytest

from cmk.plugins.aws_v2.special_agent.agent_aws_v2 import agent_aws_main, parse_arguments
from cmk.plugins.aws_v2.special_agent.config import AWSConfig, NamingConvention
from cmk.plugins.aws_v2.special_agent.runner import AWSSectionsGeneric
from cmk.plugins.aws_v2.special_agent.sections.s3 import ResultDistributorS3Limits

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


def test_failed_section_is_a_warning_naming_the_section(caplog: pytest.LogCaptureFixture) -> None:
    caplog.set_level(logging.WARNING)
    config = AWSConfig("aws-host", Args(), ([], []), NamingConvention.ip_region_instance)
    config.add_single_service_config("ebs_names", None)
    config.add_service_tags("ebs_tags", ([], []))
    session = mock.Mock(**{"client.return_value.describe_volumes.side_effect": RuntimeError})
    sections = AWSSectionsGeneric("aws-host", session, "333333333333", output=io.StringIO())
    sections.init_sections(
        ["ebs"], "eu-central-1", config.for_account("333333333333"), ResultDistributorS3Limits(None)
    )

    sections.run(use_cache=False)

    assert ("WARNING", "ebs_summary: Collection failed: ") in [
        (r.levelname, r.getMessage()) for r in caplog.records
    ]
