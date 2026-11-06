#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import logging
from pathlib import Path

import pytest

from cmk.ccc.exceptions import MKGeneralException
from cmk.cli.engine.commands import bind as cli_bind
from cmk.cli.engine.readers import ParsedOptions as CLIParsedOptions
from cmk.cli.internal import Args as CLIArgs
from cmk.cli.internal import Command as CLICommand
from cmk.cli.internal import Context as CLIContext
from cmk.cli.internal import ExitCode as CLIExitCode
from cmk.cli.internal import GlobalOptions as CLIGlobalOptions
from cmk.cli.internal import Options as CLIOptions
from cmk.plugins.checkmk.cli.snmp import cli_command_snmptranslate, cli_command_snmpwalk


def _context(*, debug_mode: bool = False) -> CLIContext:
    return CLIContext(
        omd_root=Path("/nonexistent"),
        global_options=CLIGlobalOptions(debug=debug_mode),
        logger=logging.getLogger(__name__),
    )


def _run(
    command: CLICommand[CLIOptions],
    options: list[tuple[str, str]],
    args: CLIArgs,
    *,
    debug_mode: bool = False,
) -> CLIExitCode:
    bound = cli_bind(command, CLIParsedOptions(options, logging.getLogger(__name__)))
    return bound(_context(debug_mode=debug_mode), args)


def test_a_missing_walk_name_exits_three() -> None:
    assert _run(cli_command_snmptranslate, [], [""]) == CLIExitCode.UNKNOWN


def test_a_missing_walk_name_is_logged(caplog: pytest.LogCaptureFixture) -> None:
    with caplog.at_level(logging.ERROR):
        _run(cli_command_snmptranslate, [], [""])

    assert caplog.messages == ["Please provide the name of a SNMP walk file"]


def test_a_missing_walk_name_is_raised_through_under_debug() -> None:
    with pytest.raises(MKGeneralException, match="name of a SNMP walk file"):
        _run(cli_command_snmptranslate, [], [""], debug_mode=True)


def test_oids_and_extra_oids_together_exit_three() -> None:
    assert (
        _run(cli_command_snmpwalk, [("--oid", "1.3"), ("--extraoid", "1.4")], [])
        == CLIExitCode.UNKNOWN
    )


def test_oids_and_extra_oids_together_are_raised_through_under_debug() -> None:
    with pytest.raises(MKGeneralException, match="--oid and --extraoid"):
        _run(cli_command_snmpwalk, [("--oid", "1.3"), ("--extraoid", "1.4")], [], debug_mode=True)
