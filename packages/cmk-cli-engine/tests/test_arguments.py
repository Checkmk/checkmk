#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Sequence
from pathlib import Path
from typing import Final, NoReturn

import pytest

from cmk.cli.engine.arguments import InvalidArguments, parse, RunCommand, ShowHelp
from cmk.cli.engine.commands import (
    Command,
    Commands,
    general_options,
    Option,
    parse_sub_options,
)
from cmk.cli.internal import Args, GlobalOptions, Options


def _unreachable(
    _omd_root: Path, _global: GlobalOptions, _options: Options, _args: Args
) -> NoReturn:
    raise AssertionError("parsing must not run the command")


_COMMAND_ARGUMENT: Final = "myhost"

_ARGUMENT_EVERY_CONVERSION_ACCEPTS: Final = "inline"

_PLAIN: Final = Command(
    long_option="plain",
    short_option="p",
    handler_function=_unreachable,
    short_help="takes no argument",
)

_OTHER_PLAIN: Final = Command(
    long_option="other-plain",
    handler_function=_unreachable,
    short_help="takes no argument either",
)

_WITH_ARGUMENT: Final = Command(
    long_option="with-argument",
    handler_function=_unreachable,
    argument=True,
    argument_descr="HOST",
    short_help="needs exactly one argument",
)

# The engine runs this one when the command line names no command at all, so the
# name is not free to choose.
_CHECK: Final = Command(
    long_option="check",
    short_option="c",
    handler_function=_unreachable,
    argument=True,
    argument_descr="HOSTS",
    argument_optional=True,
    sub_options=[
        Option(long_option="keepalive", short_help="the option that implies this command"),
        # The short spelling is the command's own on purpose: in "-cc" the first
        # selects the command, and both count towards the option.
        Option(long_option="counted", short_option="c", repeat=True, short_help="counts"),
        Option(
            long_option="collected",
            argument=True,
            argument_descr="VALUE",
            repeat=True,
            short_help="collects every argument",
        ),
        Option(
            long_option="converted",
            argument=True,
            argument_descr="VALUE",
            argument_conv=str.upper,
            deprecated_long_options={"legacy-name"},
            short_help="converts its argument",
        ),
    ],
    short_help="the implicit command",
)

_COMMANDS: Final = Commands(
    plugins=[_PLAIN, _OTHER_PLAIN, _WITH_ARGUMENT, _CHECK],
    general_options=general_options(),
)


def _general_option_argv(option: Option) -> Sequence[str]:
    if option.argument:
        return [f"--{option.long_option}={_ARGUMENT_EVERY_CONVERSION_ACCEPTS}"]
    return [f"--{option.long_option}"]


def test_the_long_option_selects_its_command() -> None:
    parsed = parse(_COMMANDS, ["cmk", "--plain"])

    assert isinstance(parsed, RunCommand)
    assert parsed.command is _PLAIN


def test_the_short_option_selects_its_command() -> None:
    parsed = parse(_COMMANDS, ["cmk", "-p"])

    assert isinstance(parsed, RunCommand)
    assert parsed.command is _PLAIN


def test_a_sub_option_reaches_its_command() -> None:
    parsed = parse(_COMMANDS, ["cmk", "--check", "--keepalive"])

    assert isinstance(parsed, RunCommand)
    assert "keepalive" in parse_sub_options(parsed.command.sub_options, parsed.options)


def test_a_bare_command_shows_the_help() -> None:
    assert parse(_COMMANDS, ["cmk"]) == ShowHelp(options=[])


def test_a_general_option_alone_shows_the_help_and_hands_the_options_back() -> None:
    assert parse(_COMMANDS, ["cmk", "-v"]) == ShowHelp(options=[("-v", "")])


@pytest.mark.parametrize("option", ["--help", "-h"])
def test_the_help_option_selects_the_help_command(option: str) -> None:
    parsed = parse(_COMMANDS, ["cmk", option])

    assert isinstance(parsed, RunCommand)
    assert parsed.command.name == "help"


def test_the_first_of_two_command_options_wins() -> None:
    parsed = parse(_COMMANDS, ["cmk", "--plain", "--other-plain"])

    assert isinstance(parsed, RunCommand)
    assert parsed.command is _PLAIN


def test_a_required_command_argument_comes_off_the_option() -> None:
    parsed = parse(_COMMANDS, ["cmk", f"--with-argument={_COMMAND_ARGUMENT}"])

    assert isinstance(parsed, RunCommand)
    assert (parsed.argument, parsed.arguments) == (_COMMAND_ARGUMENT, [])


def test_an_optional_command_argument_stays_in_the_positional_arguments() -> None:
    parsed = parse(_COMMANDS, ["cmk", "--check", "host1", "host2"])

    assert isinstance(parsed, RunCommand)
    assert (parsed.argument, parsed.arguments) == ("", ["host1", "host2"])


def test_a_repeated_sub_option_is_counted() -> None:
    parsed = parse(_COMMANDS, ["cmk", "-cc", "myhost"])

    assert isinstance(parsed, RunCommand)
    assert parsed.command is _CHECK
    assert parse_sub_options(parsed.command.sub_options, parsed.options) == {"counted": 2}


def test_a_repeated_sub_option_argument_is_collected() -> None:
    parsed = parse(_COMMANDS, ["cmk", "--check", "--collected=.1.1", "--collected=.1.2", "myhost"])

    assert isinstance(parsed, RunCommand)
    assert parse_sub_options(parsed.command.sub_options, parsed.options) == {
        "collected": (".1.1", ".1.2")
    }


def test_a_sub_option_argument_is_converted() -> None:
    parsed = parse(_COMMANDS, ["cmk", "--check", "--converted=value", "myhost"])

    assert isinstance(parsed, RunCommand)
    assert parse_sub_options(parsed.command.sub_options, parsed.options) == {"converted": "VALUE"}


def test_a_deprecated_sub_option_reaches_the_option_it_replaces() -> None:
    parsed = parse(_COMMANDS, ["cmk", "--check", "--legacy-name=value", "myhost"])

    assert isinstance(parsed, RunCommand)
    assert parse_sub_options(parsed.command.sub_options, parsed.options) == {"converted": "VALUE"}


def test_one_argument_runs_the_implicit_check_command() -> None:
    parsed = parse(_COMMANDS, ["cmk", "myhost"])

    assert isinstance(parsed, RunCommand)
    assert (parsed.command.name, parsed.argument, parsed.arguments) == ("check", "", ["myhost"])


def test_a_host_and_an_address_run_the_implicit_check_command() -> None:
    parsed = parse(_COMMANDS, ["cmk", "myhost", "1.2.3.4"])

    assert isinstance(parsed, RunCommand)
    assert (parsed.command.name, parsed.arguments) == ("check", ["myhost", "1.2.3.4"])


def test_keepalive_runs_the_implicit_check_command() -> None:
    parsed = parse(_COMMANDS, ["cmk", "--keepalive"])

    assert isinstance(parsed, RunCommand)
    assert parsed.command.name == "check"


def test_more_arguments_than_a_host_and_an_address_show_the_help() -> None:
    parsed = parse(_COMMANDS, ["cmk", "host1", "host2", "host3"])

    assert isinstance(parsed, ShowHelp)


def test_an_unknown_option_is_rejected() -> None:
    parsed = parse(_COMMANDS, ["cmk", "--not-an-option"])

    assert parsed == InvalidArguments(
        "ERROR: option --not-an-option not recognized (see `cmk --help` for valid options)\n"
    )


def test_a_missing_command_argument_is_rejected() -> None:
    parsed = parse(_COMMANDS, ["cmk", "--with-argument"])

    assert parsed == InvalidArguments(
        "ERROR: option --with-argument requires argument (see `cmk --help` for valid options)\n"
    )


def test_the_rejection_names_the_program_as_it_was_called() -> None:
    parsed = parse(_COMMANDS, ["/omd/sites/mysite/bin/check_mk", "--not-an-option"])

    assert isinstance(parsed, InvalidArguments)
    assert "see `check_mk --help`" in parsed.message


@pytest.mark.parametrize("option", general_options(), ids=lambda option: option.name)
def test_a_general_option_does_not_select_a_command(option: Option) -> None:
    parsed = parse(_COMMANDS, ["cmk", *_general_option_argv(option), "myhost"])

    assert isinstance(parsed, RunCommand)
    assert parsed.command.name == "check"


@pytest.mark.parametrize("option", general_options(), ids=lambda option: option.name)
def test_a_general_option_is_handed_back_for_processing(option: Option) -> None:
    parsed = parse(_COMMANDS, ["cmk", *_general_option_argv(option), "myhost"])

    assert isinstance(parsed, RunCommand)
    assert f"--{option.long_option}" in [name for name, _argument in parsed.options]
