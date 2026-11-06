#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Sequence
from typing import Final, NoReturn

import pytest

from cmk.cli.engine.arguments import InvalidArguments as CLIInvalidArguments
from cmk.cli.engine.arguments import parse as cli_parse
from cmk.cli.engine.arguments import RunCommand as CLIRunCommand
from cmk.cli.engine.arguments import ShowHelp as CLIShowHelp
from cmk.cli.engine.commands import Commands as CLICommands
from cmk.cli.engine.commands import GetoptCommand as CLIGetoptCommand
from cmk.cli.engine.discovery import make_command as cli_make_command
from cmk.cli.engine.options import general_options as cli_general_options
from cmk.cli.engine.options import Option as CLIGetoptOption
from cmk.cli.internal import Arguments as CLIArguments
from cmk.cli.internal import Command as CLICommand
from cmk.cli.internal import ExitCode as CLIExitCode
from cmk.cli.internal import Option as CLIOption
from cmk.cli.internal import Reader as CLIReader
from cmk.cli.internal import untyped_request as cli_untyped_request


def _unreachable(_reader: CLIReader) -> NoReturn:
    raise AssertionError("parsing must not bind the command")


_COMMAND_ARGUMENT: Final = "myhost"

_ARGUMENT_EVERY_CONVERSION_ACCEPTS: Final = "inline"

_PLAIN: Final = CLIGetoptCommand(
    name="plain",
    long_option="plain",
    short_option="p",
    bind=_unreachable,
    short_help="takes no argument",
)

_OTHER_PLAIN: Final = CLIGetoptCommand(
    name="other_plain",
    long_option="other-plain",
    bind=_unreachable,
    short_help="takes no argument either",
)

_WITH_ARGUMENT: Final = CLIGetoptCommand(
    name="with_argument",
    long_option="with-argument",
    bind=_unreachable,
    argument=True,
    argument_descr="HOST",
    short_help="needs exactly one argument",
)

# The engine runs this one when the command line names no command at all, so the
# name is not free to choose.
_CHECK: Final = cli_make_command(
    CLICommand(
        name="check",
        long="check",
        short="c",
        handler=lambda *_args: CLIExitCode.SUCCESS,
        arguments=CLIArguments("HOSTS", optional=True),
        request=cli_untyped_request(
            [
                CLIOption(long="keepalive", help="the option that implies this command"),
                # The short spelling is the command's own on purpose: in "-cc" the first
                # selects the command, and both count towards the option.
                CLIOption(long="counted", short="c", repeat=True, help="counts"),
                CLIOption(
                    long="collected",
                    argument="VALUE",
                    repeat=True,
                    help="collects every argument",
                ),
                CLIOption(
                    long="renamed",
                    argument="VALUE",
                    deprecated_names=frozenset({"legacy-name"}),
                    help="takes an argument",
                ),
            ]
        ),
        help="the implicit command",
    )
)

_COMMANDS: Final = CLICommands(
    plugins=[_PLAIN, _OTHER_PLAIN, _WITH_ARGUMENT, _CHECK],
    general_options=cli_general_options(),
)


def _general_option_argv(option: CLIGetoptOption) -> Sequence[str]:
    if option.argument:
        return [f"--{option.long_option}={_ARGUMENT_EVERY_CONVERSION_ACCEPTS}"]
    return [f"--{option.long_option}"]


def test_the_long_option_selects_its_command() -> None:
    parsed = cli_parse(_COMMANDS, ["cmk", "--plain"])

    assert isinstance(parsed, CLIRunCommand)
    assert parsed.command is _PLAIN


def test_the_short_option_selects_its_command() -> None:
    parsed = cli_parse(_COMMANDS, ["cmk", "-p"])

    assert isinstance(parsed, CLIRunCommand)
    assert parsed.command is _PLAIN


def test_a_sub_option_reaches_its_command() -> None:
    parsed = cli_parse(_COMMANDS, ["cmk", "--check", "--keepalive"])

    assert isinstance(parsed, CLIRunCommand)
    assert ("--keepalive", "") in parsed.options


def test_a_bare_command_shows_the_help() -> None:
    assert cli_parse(_COMMANDS, ["cmk"]) == CLIShowHelp(options=[])


def test_a_general_option_alone_shows_the_help_and_hands_the_options_back() -> None:
    assert cli_parse(_COMMANDS, ["cmk", "-v"]) == CLIShowHelp(options=[("-v", "")])


@pytest.mark.parametrize("option", ["--help", "-h"])
def test_the_help_option_shows_the_help(option: str) -> None:
    assert isinstance(cli_parse(_COMMANDS, ["cmk", option]), CLIShowHelp)


def test_the_help_option_wins_over_a_command_before_it() -> None:
    assert isinstance(cli_parse(_COMMANDS, ["cmk", "--plain", "--help"]), CLIShowHelp)


def test_the_first_of_two_command_options_wins() -> None:
    parsed = cli_parse(_COMMANDS, ["cmk", "--plain", "--other-plain"])

    assert isinstance(parsed, CLIRunCommand)
    assert parsed.command is _PLAIN


def test_a_required_command_argument_comes_off_the_option() -> None:
    parsed = cli_parse(_COMMANDS, ["cmk", f"--with-argument={_COMMAND_ARGUMENT}"])

    assert isinstance(parsed, CLIRunCommand)
    assert (parsed.argument, parsed.arguments) == (_COMMAND_ARGUMENT, [])


def test_an_optional_command_argument_stays_in_the_positional_arguments() -> None:
    parsed = cli_parse(_COMMANDS, ["cmk", "--check", "host1", "host2"])

    assert isinstance(parsed, CLIRunCommand)
    assert (parsed.argument, parsed.arguments) == ("", ["host1", "host2"])


def test_a_repeated_short_spelling_selects_the_command_and_stays_an_option() -> None:
    parsed = cli_parse(_COMMANDS, ["cmk", "-cc", "myhost"])

    assert isinstance(parsed, CLIRunCommand)
    assert (parsed.command, parsed.options) == (_CHECK, [("-c", ""), ("-c", "")])


def test_a_repeated_sub_option_argument_is_kept_every_time() -> None:
    parsed = cli_parse(
        _COMMANDS, ["cmk", "--check", "--collected=.1.1", "--collected=.1.2", "myhost"]
    )

    assert isinstance(parsed, CLIRunCommand)
    assert parsed.options == [("--check", ""), ("--collected", ".1.1"), ("--collected", ".1.2")]


def test_a_deprecated_sub_option_is_kept_under_its_own_spelling() -> None:
    parsed = cli_parse(_COMMANDS, ["cmk", "--check", "--legacy-name=value", "myhost"])

    assert isinstance(parsed, CLIRunCommand)
    assert parsed.options == [("--check", ""), ("--legacy-name", "value")]


def test_one_argument_runs_the_implicit_check_command() -> None:
    parsed = cli_parse(_COMMANDS, ["cmk", "myhost"])

    assert isinstance(parsed, CLIRunCommand)
    assert (parsed.command.name, parsed.argument, parsed.arguments) == ("check", "", ["myhost"])


def test_a_host_and_an_address_run_the_implicit_check_command() -> None:
    parsed = cli_parse(_COMMANDS, ["cmk", "myhost", "1.2.3.4"])

    assert isinstance(parsed, CLIRunCommand)
    assert (parsed.command.name, parsed.arguments) == ("check", ["myhost", "1.2.3.4"])


def test_keepalive_runs_the_implicit_check_command() -> None:
    parsed = cli_parse(_COMMANDS, ["cmk", "--keepalive"])

    assert isinstance(parsed, CLIRunCommand)
    assert parsed.command.name == "check"


def test_more_arguments_than_a_host_and_an_address_show_the_help() -> None:
    parsed = cli_parse(_COMMANDS, ["cmk", "host1", "host2", "host3"])

    assert isinstance(parsed, CLIShowHelp)


def test_an_unknown_option_is_rejected() -> None:
    parsed = cli_parse(_COMMANDS, ["cmk", "--not-an-option"])

    assert parsed == CLIInvalidArguments(
        "ERROR: option --not-an-option not recognized (see `cmk --help` for valid options)\n"
    )


def test_a_missing_command_argument_is_rejected() -> None:
    parsed = cli_parse(_COMMANDS, ["cmk", "--with-argument"])

    assert parsed == CLIInvalidArguments(
        "ERROR: option --with-argument requires argument (see `cmk --help` for valid options)\n"
    )


def test_the_rejection_names_the_program_as_it_was_called() -> None:
    parsed = cli_parse(_COMMANDS, ["/omd/sites/mysite/bin/check_mk", "--not-an-option"])

    assert isinstance(parsed, CLIInvalidArguments)
    assert "see `check_mk --help`" in parsed.message


@pytest.mark.parametrize("option", cli_general_options(), ids=lambda option: option.name)
def test_a_general_option_does_not_select_a_command(option: CLIGetoptOption) -> None:
    parsed = cli_parse(_COMMANDS, ["cmk", *_general_option_argv(option), "myhost"])

    assert isinstance(parsed, CLIRunCommand)
    assert parsed.command.name == "check"


@pytest.mark.parametrize("option", cli_general_options(), ids=lambda option: option.name)
def test_a_general_option_is_handed_back_for_processing(option: CLIGetoptOption) -> None:
    parsed = cli_parse(_COMMANDS, ["cmk", *_general_option_argv(option), "myhost"])

    assert isinstance(parsed, CLIRunCommand)
    assert f"--{option.long_option}" in [name for name, _argument in parsed.options]
