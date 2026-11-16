#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import re
from pathlib import Path
from typing import Final

import pytest

from cmk.cli.engine.commands import Commands as CLICommands
from cmk.cli.engine.commands import takes_value as cli_takes_value
from cmk.cli.engine.discovery import _named_after_its_variable as _cli_named_after_its_variable
from cmk.cli.engine.discovery import load_handler as cli_load_handler
from cmk.cli.engine.discovery import make_command as cli_make_command
from cmk.cli.engine.readers import parsed as cli_parsed
from cmk.cli.internal import Argument as CLIArgument
from cmk.cli.internal import Arguments as CLIArguments
from cmk.cli.internal import Command as CLICommand
from cmk.cli.internal import Context as CLIContext
from cmk.cli.internal import Count as CLICount
from cmk.cli.internal import ExitCode as CLIExitCode
from cmk.cli.internal import GlobalOptions as CLIGlobalOptions
from cmk.cli.internal import Handler as CLIHandler
from cmk.cli.internal import no_options as cli_no_options
from cmk.cli.internal import OptionalArgument as CLIOptionalArgument
from cmk.cli.internal import Reader as CLIReader
from cmk.cli.internal import Value as CLIValue
from cmk.discover_plugins import PluginLocation

from ._commands import command_reading, command_with, HANDED_IN
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


def _handler(_context: CLIContext, _request: tuple[str | None, int]) -> CLIExitCode:
    return CLIExitCode.SUCCESS


def test_make_command_records_the_options_a_command_declares() -> None:
    command = command_with(
        CLICommand(
            name="snmpwalk",
            handler=HANDED_IN,
            long="snmpwalk",
            request=_walk_request,
            help="Walk",
        ),
        _handler,
    )
    assert command.options == [_OID_VALUE, _VERBOSE_COUNT]


def test_binding_a_command_does_not_load_its_handler() -> None:
    loaded: list[str] = []

    def load() -> CLIHandler[tuple[str | None, int]]:
        loaded.append("handler")
        raise AssertionError("loaded")

    cli_make_command(
        CLICommand(
            name="snmpwalk", handler=HANDED_IN, long="snmpwalk", request=_walk_request, help="Walk"
        ),
        load,
    ).bind(cli_parsed([("--oid", "iso")], {}, null_logger()))

    assert loaded == []


def test_a_commands_handler_receives_its_request_parsed() -> None:
    seen: list[tuple[str | None, int]] = []

    def _record(_context: CLIContext, request: tuple[str | None, int]) -> CLIExitCode:
        seen.append(request)
        return CLIExitCode.SUCCESS

    command = command_with(
        CLICommand(
            name="snmpwalk",
            handler=HANDED_IN,
            long="snmpwalk",
            request=_walk_request,
            help="Walk",
        ),
        _record,
    )
    bound = command.bind(
        cli_parsed([("--oid", "iso"), ("--verbose", ""), ("--verbose", "")], {}, null_logger())
    )

    bound(
        CLIContext(
            omd_root=_OMD_ROOT,
            global_options=CLIGlobalOptions(),
            logger=null_logger(),
        )
    )

    assert seen == [("ISO", 2)]


def test_a_command_not_named_after_its_variable_is_rejected() -> None:
    command = CLICommand(
        name="demo",
        handler=HANDED_IN,
        long="demo",
        request=_walk_request,
        help="Demonstrate",
    )

    with pytest.raises(ValueError, match="not named after its command"):
        _cli_named_after_its_variable(
            "cli_command_", PluginLocation("family.cli.demo", "cli_command_other"), command
        )


def _greeting(name: str, handler: str) -> CLICommand[None]:
    return CLICommand(name=name, handler=handler, long=name, request=cli_no_options, help="Greet")


def _greet(_context: CLIContext, _request: None) -> CLIExitCode:
    return CLIExitCode.SUCCESS


_GREET: Final = _greeting("greet", f"{__name__}:cli_handler_greet")

cli_handler_greet = CLIHandler(command=_GREET, run=_greet)


def test_a_command_loads_the_handler_it_refers_to() -> None:
    assert cli_load_handler(_GREET) is cli_handler_greet


def test_a_reference_without_an_object_is_rejected() -> None:
    with pytest.raises(ValueError, match="'family.cli.handlers' does not refer to a handler"):
        cli_load_handler(_greeting("greet", "family.cli.handlers"))


def test_a_reference_to_a_missing_object_is_reported() -> None:
    with pytest.raises(LookupError, match=re.escape(f"{__name__} has no cli_handler_missing")):
        cli_load_handler(_greeting("greet", f"{__name__}:cli_handler_missing"))


def test_a_reference_to_something_else_is_reported() -> None:
    with pytest.raises(TypeError, match="is a function, not a Handler"):
        cli_load_handler(_greeting("greet", f"{__name__}:_greet"))


def test_the_handler_of_another_command_is_rejected() -> None:
    with pytest.raises(ValueError, match="handles 'greet', not 'farewell'"):
        cli_load_handler(_greeting("farewell", f"{__name__}:cli_handler_greet"))


_HOST_ARGUMENT = CLIArgument(placeholder="HOST", parse=str)

_ADDRESS_ARGUMENT = CLIOptionalArgument(placeholder="ADDRESS", parse=str)

_NUMBERS_ARGUMENTS = CLIArguments(placeholder="N...", parse=int)


def test_a_single_required_argument_is_the_command_options_value() -> None:
    command = command_reading(lambda options: options.argument(_HOST_ARGUMENT))

    assert cli_takes_value(command)


def test_more_arguments_are_the_rest_of_the_command_line() -> None:
    command = command_reading(lambda options: options.arguments(_NUMBERS_ARGUMENTS))

    assert not cli_takes_value(command)


def test_the_help_brackets_the_arguments_a_command_line_may_leave_out() -> None:
    def request(options: CLIReader) -> object:
        return (
            options.argument(_HOST_ARGUMENT),
            options.argument(_ADDRESS_ARGUMENT),
            options.arguments(_NUMBERS_ARGUMENTS),
        )

    assert (
        "--thing HOST [ADDRESS] [N...] " in CLICommands(commands=[command_reading(request)]).help()
    )


def test_a_required_argument_after_an_optional_one_is_rejected() -> None:
    with pytest.raises(ValueError, match="'thing' reads a required argument after an optional one"):
        command_reading(
            lambda options: (
                options.argument(_ADDRESS_ARGUMENT),
                options.argument(_HOST_ARGUMENT),
            )
        )


def test_an_argument_after_the_remaining_ones_is_rejected() -> None:
    with pytest.raises(ValueError, match="'thing' reads an argument after its remaining arguments"):
        command_reading(
            lambda options: (
                options.arguments(_NUMBERS_ARGUMENTS),
                options.argument(_ADDRESS_ARGUMENT),
            )
        )


def test_a_command_reading_a_positional_argument_twice_is_rejected() -> None:
    with pytest.raises(ValueError, match="'thing' reads a positional argument twice"):
        command_reading(
            lambda options: (
                options.argument(_HOST_ARGUMENT),
                options.arguments(CLIArguments(placeholder="HOST", parse=str)),
            )
        )
