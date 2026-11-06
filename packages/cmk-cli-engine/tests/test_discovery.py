#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from contextlib import nullcontext
from pathlib import Path
from typing import Final

import pytest

from cmk.cli.engine.arguments import RunCommand as CLIRunCommand
from cmk.cli.engine.call import call as cli_call
from cmk.cli.engine.discovery import _named_after_its_variable as _cli_named_after_its_variable
from cmk.cli.engine.discovery import make_command as cli_make_command
from cmk.cli.engine.readers import ParsedOptions as CLIParsedOptions
from cmk.cli.internal import Args as CLIArgs
from cmk.cli.internal import Arguments as CLIArguments
from cmk.cli.internal import Command as CLICommand
from cmk.cli.internal import Context as CLIContext
from cmk.cli.internal import ExitCode as CLIExitCode
from cmk.cli.internal import GlobalOptions as CLIGlobalOptions
from cmk.cli.internal import Option as CLIOption
from cmk.cli.internal import Options as CLIOptions
from cmk.cli.internal import untyped_request as cli_untyped_request
from cmk.discover_plugins import PluginLocation

from ._logger import null_logger

# The engine only hands this through to the command's handler.
_OMD_ROOT: Final = Path("/omd/sites/mysite")


def _handler(_context: CLIContext, _options: CLIOptions, _args: CLIArgs) -> CLIExitCode:
    return CLIExitCode.SUCCESS


def test_make_command_records_the_options_a_command_declares() -> None:
    command = cli_make_command(
        CLICommand(
            name="snmpwalk",
            long="snmpwalk",
            handler=_handler,
            help="Walk",
            request=cli_untyped_request(
                [
                    CLIOption(
                        long="oid",
                        help="Walk the given OID",
                        argument="OID",
                        deprecated_names=frozenset({"object"}),
                    ),
                    CLIOption(long="verbose", help="Be verbose", repeat=True),
                ]
            ),
        )
    )
    assert command.long_getopt_specs() == ["snmpwalk", "oid=", "object=", "verbose"]


def test_a_commands_handler_receives_its_options_converted() -> None:
    seen: list[CLIOptions] = []

    def _record(_context: CLIContext, options: CLIOptions, _args: CLIArgs) -> CLIExitCode:
        seen.append(options)
        return CLIExitCode.SUCCESS

    command = cli_make_command(
        CLICommand(
            name="snmpwalk",
            long="snmpwalk",
            handler=_record,
            help="Walk",
            request=cli_untyped_request(
                [
                    CLIOption(
                        long="oid",
                        help="Walk the given OID",
                        argument="OID",
                        parse=str.upper,
                    ),
                    CLIOption(long="verbose", help="Be verbose", repeat=True),
                ]
            ),
        )
    )
    bound = command.bind(
        CLIParsedOptions([("--oid", "iso"), ("--verbose", ""), ("--verbose", "")], null_logger())
    )

    bound(
        CLIContext(omd_root=_OMD_ROOT, global_options=CLIGlobalOptions(), logger=null_logger()),
        [],
    )

    assert seen == [{"oid": "ISO", "verbose": 2}]


@pytest.mark.parametrize(
    ["arguments", "argument", "expected_args"],
    [
        pytest.param(None, "", [], id="no argument: nothing is passed"),
        pytest.param(
            CLIArguments("ARG"),
            "ARG",
            ["ARG"],
            id="required argument: exactly the option's argument",
        ),
        pytest.param(
            CLIArguments("ARG", optional=True),
            "ARG",
            ["ARG", "more"],
            id="optional argument: all remaining arguments",
        ),
    ],
)
def test_call_shapes_the_positional_arguments(
    arguments: CLIArguments | None, argument: str, expected_args: list[str]
) -> None:
    seen: list[CLIArgs] = []

    def _record(_context: CLIContext, _options: CLIOptions, args: CLIArgs) -> CLIExitCode:
        seen.append(args)
        return CLIExitCode.ERROR

    command = cli_make_command(
        CLICommand(
            name="thing",
            long="thing",
            request=cli_untyped_request(),
            handler=_record,
            help="Do the thing",
            arguments=arguments,
        )
    )
    run_command = CLIRunCommand(
        command,
        argument,
        [("--thing", argument)],
        ["ARG", "more"],
    )
    exit_status = cli_call(
        CLIContext(omd_root=_OMD_ROOT, global_options=CLIGlobalOptions(), logger=null_logger()),
        run_command,
        command.bind(CLIParsedOptions(run_command.options, null_logger())),
        lambda *_args: nullcontext(),
    )
    assert exit_status == CLIExitCode.ERROR
    assert [list(args) for args in seen] == [expected_args]


def test_a_command_not_named_after_its_variable_is_rejected() -> None:
    command = CLICommand(
        name="demo",
        long="demo",
        request=cli_untyped_request(),
        handler=_handler,
        help="Demonstrate",
    )

    with pytest.raises(ValueError, match="not named after its command"):
        _cli_named_after_its_variable(
            PluginLocation("family.cli.demo", "cli_command_other"), command
        )
