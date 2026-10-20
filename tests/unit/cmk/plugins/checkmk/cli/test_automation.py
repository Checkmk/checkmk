#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import logging
import shlex
from logging.handlers import BufferingHandler
from pathlib import Path

import pytest

from cmk.automations.backends import SubprocessExecutor
from cmk.automations.engine import AutomationError
from cmk.automations.internal import AutomationID
from cmk.ccc.exceptions import MKBailOut
from cmk.cli.engine.arguments import parse, RunCommand
from cmk.cli.engine.commands import Commands, general_options, make_command, parse_sub_options
from cmk.cli.internal import CommandContext, ExitCode, GlobalOptions
from cmk.plugins.checkmk.cli.automation import _automation_error_exit_code, cli_command_automation


def test_the_version_of_a_subprocess_automation_reaches_the_cli() -> None:
    argv = shlex.split(
        SubprocessExecutor().command_description(
            AutomationID("service-discovery-preview"),
            ["myhost"],
            None,
            for_cmk_version="2.4.0p1",
        )
    )

    parsed = parse(
        Commands(plugins=[make_command(cli_command_automation)], general_options=general_options()),
        argv,
    )

    assert isinstance(parsed, RunCommand)
    assert parse_sub_options(
        parsed.command.sub_options, parsed.options, logging.getLogger(__name__)
    ) == {"for-cmk-version": "2.4.0p1"}
    assert parsed.arguments == ["service-discovery-preview", "myhost"]


def _context(global_options: GlobalOptions) -> CommandContext:
    return CommandContext(
        omd_root=Path("/nonexistent"),
        global_options=global_options,
        logger=logging.getLogger(__name__),
    )


def test_an_invalid_version_is_rejected_before_the_automation_runs() -> None:
    with pytest.raises(MKBailOut, match="--for-cmk-version"):
        # Running "restart" for real would fail without a site: the error must come first.
        cli_command_automation.handler_function(
            _context(GlobalOptions(debug=True)), {"for-cmk-version": "foo"}, ["restart"]
        )


def test_an_invalid_version_exits_three() -> None:
    assert (
        cli_command_automation.handler_function(
            _context(GlobalOptions()), {"for-cmk-version": "foo"}, ["restart"]
        )
        == ExitCode.UNKNOWN
    )


def test_an_invalid_version_is_reported_through_the_context_logger() -> None:
    recorded = BufferingHandler(capacity=10)
    logger = logging.getLogger(f"{__name__}.recorded")
    logger.propagate = False
    logger.handlers = [recorded]

    cli_command_automation.handler_function(
        CommandContext(
            omd_root=Path("/nonexistent"), global_options=GlobalOptions(), logger=logger
        ),
        {"for-cmk-version": "foo"},
        ["restart"],
    )

    assert recorded.buffer[0].getMessage().startswith("--for-cmk-version:")


@pytest.mark.parametrize(
    ["error", "expected"],
    [
        (AutomationError.KNOWN_ERROR, ExitCode.FAILURE),
        (AutomationError.UNKNOWN_ERROR, ExitCode.ERROR),
    ],
)
def test_an_automation_error_exits_with_its_value(
    error: AutomationError, expected: ExitCode
) -> None:
    assert _automation_error_exit_code(error) == expected
