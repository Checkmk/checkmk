#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


import pytest

from cmk.cli.internal import ExitCode as CLIExitCode
from cmk.plugins.checkmk.cli.handlers.localize import cli_handler_localize

from ._context import context


@pytest.mark.parametrize(
    "args", [[], ["frobnicate", "de"]], ids=["without a command", "with an unknown command"]
)
def test_a_wrong_invocation_fails(args: list[str]) -> None:
    assert cli_handler_localize.run(context(), args) == CLIExitCode.FAILURE


def test_a_call_without_a_command_shows_the_usage_on_stderr(
    capsys: pytest.CaptureFixture[str],
) -> None:
    cli_handler_localize.run(context(), [])

    assert "Usage:" in capsys.readouterr().err
