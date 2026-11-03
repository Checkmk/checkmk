#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from contextlib import nullcontext
from pathlib import Path
from typing import Final

import pytest

from cmk.cli.engine.call import call
from cmk.cli.engine.commands import (
    _named_after_its_variable,
    make_command,
    make_option,
    parse_sub_options,
)
from cmk.cli.internal import Args as CLIArgs
from cmk.cli.internal import Arguments as CLIArguments
from cmk.cli.internal import Command as CLICommand
from cmk.cli.internal import Context as CLIContext
from cmk.cli.internal import ExitCode as CLIExitCode
from cmk.cli.internal import GlobalOptions as CLIGlobalOptions
from cmk.cli.internal import Option as CLIOption
from cmk.cli.internal import Options
from cmk.discover_plugins import PluginLocation

from ._logger import null_logger

# The engine only hands this through to the command's handler.
_OMD_ROOT: Final = Path("/omd/sites/mysite")


def _handler(_context: CLIContext, _options: Options, _args: CLIArgs) -> CLIExitCode:
    return CLIExitCode.SUCCESS


def test_make_option_keeps_deprecated_long_options() -> None:
    option = make_option(
        CLIOption(
            long="plugins",
            help="Restrict to the given plug-ins",
            argument="PLUGINS",
            deprecated_names=frozenset({"checks"}),
        )
    )
    assert option.long_getopt_specs() == ["plugins=", "checks="]
    assert option.is_deprecated_option("--checks")


def test_make_command_parses_sub_options_with_conversion() -> None:
    command = make_command(
        CLICommand(
            name="snmpwalk",
            long="snmpwalk",
            handler_function=_handler,
            help="Walk",
            sub_options=[
                CLIOption(
                    long="oid",
                    help="Walk the given OID",
                    argument="OID",
                    parse=str.upper,
                ),
                CLIOption(long="verbose", help="Be verbose", repeat=True),
            ],
        )
    )
    assert parse_sub_options(
        command.sub_options, [("--oid", "iso"), ("--verbose", ""), ("--verbose", "")], null_logger()
    ) == {
        "oid": "ISO",
        "verbose": 2,
    }


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

    def _record(_context: CLIContext, _options: Options, args: CLIArgs) -> CLIExitCode:
        seen.append(args)
        return CLIExitCode.ERROR

    command = make_command(
        CLICommand(
            name="thing",
            long="thing",
            handler_function=_record,
            help="Do the thing",
            arguments=arguments,
        )
    )
    exit_status = call(
        CLIContext(omd_root=_OMD_ROOT, global_options=CLIGlobalOptions(), logger=null_logger()),
        command,
        argument,
        parse_sub_options(command.sub_options, [("--thing", argument)], null_logger()),
        ["ARG", "more"],
        lambda *_args: nullcontext(),
    )
    assert exit_status == CLIExitCode.ERROR
    assert [list(args) for args in seen] == [expected_args]


def test_a_command_not_named_after_its_variable_is_rejected() -> None:
    command = CLICommand(
        name="demo",
        long="demo",
        handler_function=_handler,
        help="Demonstrate",
    )

    with pytest.raises(ValueError, match="not named after its command"):
        _named_after_its_variable(PluginLocation("family.cli.demo", "cli_command_other"), command)
