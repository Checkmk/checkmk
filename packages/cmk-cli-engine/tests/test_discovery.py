#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from pathlib import Path
from typing import Final

import pytest

from cmk.cli.engine.discovery import _named_after_its_variable as _cli_named_after_its_variable
from cmk.cli.engine.discovery import make_command as cli_make_command
from cmk.cli.engine.readers import ParsedOptions as CLIParsedOptions
from cmk.cli.internal import Args as CLIArgs
from cmk.cli.internal import Command as CLICommand
from cmk.cli.internal import Context as CLIContext
from cmk.cli.internal import Count as CLICount
from cmk.cli.internal import ExitCode as CLIExitCode
from cmk.cli.internal import GlobalOptions as CLIGlobalOptions
from cmk.cli.internal import no_options as cli_no_options
from cmk.cli.internal import Reader as CLIReader
from cmk.cli.internal import Value as CLIValue
from cmk.discover_plugins import PluginLocation

from ._logger import null_logger

# The engine only hands this through to the command's handler.
_OMD_ROOT: Final = Path("/omd/sites/mysite")


_OID_VALUE: Final = CLIValue(
    long="oid",
    help="Walk the given OID",
    placeholder="OID",
    deprecated_names=frozenset({"object"}),
    parse=str.upper,
)

_VERBOSE_COUNT: Final = CLICount(long="verbose", help="Be verbose")


def _walk_request(options: CLIReader) -> tuple[str | None, int]:
    return options.value(_OID_VALUE), options.count(_VERBOSE_COUNT)


def _handler(_context: CLIContext, _request: tuple[str | None, int], _args: CLIArgs) -> CLIExitCode:
    return CLIExitCode.SUCCESS


def test_make_command_records_the_options_a_command_declares() -> None:
    command = cli_make_command(
        CLICommand(
            name="snmpwalk",
            long="snmpwalk",
            request=_walk_request,
            handler=_handler,
            help="Walk",
        )
    )
    assert command.options == [_OID_VALUE, _VERBOSE_COUNT]


def test_a_commands_handler_receives_its_request_parsed() -> None:
    seen: list[tuple[str | None, int]] = []

    def _record(
        _context: CLIContext, request: tuple[str | None, int], _args: CLIArgs
    ) -> CLIExitCode:
        seen.append(request)
        return CLIExitCode.SUCCESS

    command = cli_make_command(
        CLICommand(
            name="snmpwalk",
            long="snmpwalk",
            request=_walk_request,
            handler=_record,
            help="Walk",
        )
    )
    bound = command.bind(
        CLIParsedOptions([("--oid", "iso"), ("--verbose", ""), ("--verbose", "")], null_logger())
    )

    bound(
        CLIContext(omd_root=_OMD_ROOT, global_options=CLIGlobalOptions(), logger=null_logger()),
        [],
    )

    assert seen == [("ISO", 2)]


def test_a_command_not_named_after_its_variable_is_rejected() -> None:
    command = CLICommand(
        name="demo",
        long="demo",
        request=cli_no_options,
        handler=lambda *_args: CLIExitCode.SUCCESS,
        help="Demonstrate",
    )

    with pytest.raises(ValueError, match="not named after its command"):
        _cli_named_after_its_variable(
            "cli_command_", PluginLocation("family.cli.demo", "cli_command_other"), command
        )
