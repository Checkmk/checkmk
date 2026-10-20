#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from pathlib import Path
from typing import Final

import pytest

from cmk import trace
from cmk.cli.engine.call import call
from cmk.cli.engine.commands import make_command, make_option, parse_sub_options
from cmk.cli.internal import Args, CLICommand, CLIOption, ExitCode, GlobalOptions, Options

from ._logger import null_logger

# The engine only hands this through to the command's handler.
_OMD_ROOT: Final = Path("/omd/sites/mysite")


def _handler(
    _omd_root: Path, _global_options: GlobalOptions, _options: Options, _args: Args
) -> ExitCode:
    return ExitCode.SUCCESS


def test_make_option_keeps_deprecated_long_options() -> None:
    option = make_option(
        CLIOption(
            long_option="plugins",
            short_help="Restrict to the given plug-ins",
            argument=True,
            argument_descr="PLUGINS",
            deprecated_long_options=frozenset({"checks"}),
        )
    )
    assert option.long_getopt_specs() == ["plugins=", "checks="]
    assert option.is_deprecated_option("--checks")


def test_make_command_parses_sub_options_with_conversion() -> None:
    command = make_command(
        CLICommand(
            long_option="snmpwalk",
            handler_function=_handler,
            short_help="Walk",
            sub_options=[
                CLIOption(
                    long_option="oid",
                    short_help="Walk the given OID",
                    argument=True,
                    argument_descr="OID",
                    argument_conv=str.upper,
                ),
                CLIOption(long_option="verbose", short_help="Be verbose", repeat=True),
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
    ["argument", "argument_optional", "expected_args"],
    [
        pytest.param(False, False, [], id="no argument: nothing is passed"),
        pytest.param(True, False, ["ARG"], id="required argument: exactly the option's argument"),
        pytest.param(True, True, ["ARG", "more"], id="optional argument: all remaining arguments"),
    ],
)
def test_call_shapes_the_positional_arguments(
    argument: bool, argument_optional: bool, expected_args: list[str]
) -> None:
    seen: list[Args] = []

    def _record(
        _omd_root: Path, _global_options: GlobalOptions, _options: Options, args: Args
    ) -> ExitCode:
        seen.append(args)
        return ExitCode.ERROR

    command = make_command(
        CLICommand(
            long_option="thing",
            handler_function=_record,
            short_help="Do the thing",
            argument=argument,
            argument_descr="ARG" if argument else None,
            argument_optional=argument_optional,
        )
    )
    exit_status = call(
        _OMD_ROOT,
        command,
        GlobalOptions(),
        "ARG" if argument else "",
        parse_sub_options(
            command.sub_options, [("--thing", "ARG" if argument else "")], null_logger()
        ),
        ["ARG", "more"],
        trace.extract_context_from_environment({}),
    )
    assert exit_status == ExitCode.ERROR
    assert [list(args) for args in seen] == [expected_args]
