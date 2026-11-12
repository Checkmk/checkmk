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
from cmk.cli.engine.discovery import make_command as cli_make_command
from cmk.cli.engine.options import _GENERAL_OPTIONS as CLI_GENERAL_OPTIONS
from cmk.cli.engine.options import Declaration as CLIDeclaration
from cmk.cli.engine.options import GlobalOptions as CLIEngineGlobalOptions
from cmk.cli.engine.options import placeholder as cli_placeholder
from cmk.cli.internal import Args as CLIArgs
from cmk.cli.internal import Arguments as CLIArguments
from cmk.cli.internal import Command as CLICommand
from cmk.cli.internal import Context as CLIContext
from cmk.cli.internal import Count as CLICount
from cmk.cli.internal import ExitCode as CLIExitCode
from cmk.cli.internal import Flag as CLIFlag
from cmk.cli.internal import no_options as cli_no_options
from cmk.cli.internal import Reader as CLIReader
from cmk.cli.internal import Value as CLIValue
from cmk.cli.internal import Values as CLIValues

from ._logger import null_logger


def _unreachable(_context: CLIContext, _request: None, _args: CLIArgs) -> NoReturn:
    raise AssertionError("parsing must not run the command")


_COMMAND_ARGUMENT: Final = "myhost"

_ARGUMENT_EVERY_CONVERSION_ACCEPTS: Final = "inline"

_PLAIN: Final = cli_make_command(
    CLICommand(
        name="plain",
        long="plain",
        short="p",
        request=cli_no_options,
        handler=_unreachable,
        help="takes no argument",
    )
)

_OTHER_PLAIN: Final = cli_make_command(
    CLICommand(
        name="other_plain",
        long="other-plain",
        request=cli_no_options,
        handler=_unreachable,
        help="takes no argument either",
    )
)

_WITH_ARGUMENT: Final = cli_make_command(
    CLICommand(
        name="with_argument",
        long="with-argument",
        request=cli_no_options,
        handler=_unreachable,
        arguments=CLIArguments("HOST"),
        help="needs exactly one argument",
    )
)

_FLAG: Final = CLIFlag(long="flag", help="a flag")

# The short spelling is the command's own on purpose: in "-cc" the first
# selects the command, and both count towards the option.
_COUNTED_COUNT: Final = CLICount(long="counted", short="c", help="counts")

_COLLECTED_VALUES: Final = CLIValues(
    long="collected",
    placeholder="VALUE",
    help="collects every argument",
    parse=str,
)

_RENAMED_VALUE: Final = CLIValue(
    long="renamed",
    placeholder="VALUE",
    deprecated_names=frozenset({"legacy-name"}),
    help="takes an argument",
    parse=str,
)


def _default_request(
    options: CLIReader,
) -> tuple[bool, int, Sequence[str], str | None]:
    return (
        options.flag(_FLAG),
        options.count(_COUNTED_COUNT),
        options.values(_COLLECTED_VALUES),
        options.value(_RENAMED_VALUE),
    )


_DEFAULT: Final = cli_make_command(
    CLICommand(
        name="default",
        long="default",
        short="c",
        request=_default_request,
        handler=lambda *_args: CLIExitCode.SUCCESS,
        arguments=CLIArguments("HOSTS", optional=True),
        default=True,
        help="the default command",
    )
)

_COMMANDS: Final = CLICommands(commands=[_PLAIN, _OTHER_PLAIN, _WITH_ARGUMENT, _DEFAULT])


def _parse(argv: Sequence[str]) -> CLIRunCommand | CLIShowHelp | CLIInvalidArguments:
    return cli_parse(_COMMANDS, argv, null_logger())


def _general_option_argv(option: CLIDeclaration) -> Sequence[str]:
    if cli_placeholder(option) is not None:
        return [f"--{option.long}={_ARGUMENT_EVERY_CONVERSION_ACCEPTS}"]
    return [f"--{option.long}"]


def test_the_long_option_selects_its_command() -> None:
    parsed = _parse(["cmk", "--plain"])

    assert isinstance(parsed, CLIRunCommand)
    assert parsed.command is _PLAIN


def test_the_short_option_selects_its_command() -> None:
    parsed = _parse(["cmk", "-p"])

    assert isinstance(parsed, CLIRunCommand)
    assert parsed.command is _PLAIN


def test_a_sub_option_reaches_its_command() -> None:
    parsed = _parse(["cmk", "--default", "--flag"])

    assert isinstance(parsed, CLIRunCommand)
    assert ("--flag", "") in parsed.options


def test_a_bare_command_shows_the_help() -> None:
    assert _parse(["cmk"]) == CLIShowHelp(CLIEngineGlobalOptions())


def test_a_general_option_alone_shows_the_help_with_the_general_options() -> None:
    assert _parse(["cmk", "-v"]) == CLIShowHelp(CLIEngineGlobalOptions(verbosity=1))


@pytest.mark.parametrize("option", ["--help", "-h"])
def test_the_help_option_shows_the_help(option: str) -> None:
    assert isinstance(_parse(["cmk", option]), CLIShowHelp)


def test_the_help_option_wins_over_a_command_before_it() -> None:
    assert isinstance(_parse(["cmk", "--plain", "--help"]), CLIShowHelp)


def test_the_first_of_two_command_options_wins() -> None:
    parsed = _parse(["cmk", "--plain", "--other-plain"])

    assert isinstance(parsed, CLIRunCommand)
    assert parsed.command is _PLAIN


def test_a_required_command_argument_comes_off_the_option() -> None:
    parsed = _parse(["cmk", f"--with-argument={_COMMAND_ARGUMENT}"])

    assert isinstance(parsed, CLIRunCommand)
    assert parsed.args == [_COMMAND_ARGUMENT]


def test_a_command_without_argument_receives_no_arguments() -> None:
    parsed = _parse(["cmk", "--plain", "ignored", "too"])

    assert isinstance(parsed, CLIRunCommand)
    assert parsed.args == ()


def test_an_optional_command_argument_takes_all_positional_arguments() -> None:
    parsed = _parse(["cmk", "--default", "host1", "host2"])

    assert isinstance(parsed, CLIRunCommand)
    assert parsed.args == ["host1", "host2"]


def test_a_repeated_short_spelling_selects_the_command_and_stays_an_option() -> None:
    parsed = _parse(["cmk", "-cc", "myhost"])

    assert isinstance(parsed, CLIRunCommand)
    assert (parsed.command, parsed.options) == (_DEFAULT, [("-c", ""), ("-c", "")])


def test_a_repeated_sub_option_argument_is_kept_every_time() -> None:
    parsed = _parse(["cmk", "--default", "--collected=.1.1", "--collected=.1.2", "myhost"])

    assert isinstance(parsed, CLIRunCommand)
    assert parsed.options == [("--default", ""), ("--collected", ".1.1"), ("--collected", ".1.2")]


def test_a_deprecated_sub_option_is_kept_under_its_own_spelling() -> None:
    parsed = _parse(["cmk", "--default", "--legacy-name=value", "myhost"])

    assert isinstance(parsed, CLIRunCommand)
    assert parsed.options == [("--default", ""), ("--legacy-name", "value")]


def test_positional_arguments_alone_run_the_default_command() -> None:
    parsed = _parse(["cmk", "myhost", "1.2.3.4"])

    assert isinstance(parsed, CLIRunCommand)
    assert (parsed.command, parsed.args) == (_DEFAULT, ["myhost", "1.2.3.4"])


def test_without_a_default_command_positional_arguments_show_the_help() -> None:
    commands = CLICommands(commands=[_PLAIN])

    assert isinstance(cli_parse(commands, ["cmk", "myhost"], null_logger()), CLIShowHelp)


def test_an_unknown_option_is_rejected() -> None:
    parsed = _parse(["cmk", "--not-an-option"])

    assert parsed == CLIInvalidArguments(
        "ERROR: option --not-an-option not recognized (see `cmk --help` for valid options)\n"
    )


def test_a_missing_command_argument_is_rejected() -> None:
    parsed = _parse(["cmk", "--with-argument"])

    assert parsed == CLIInvalidArguments(
        "ERROR: option --with-argument requires argument (see `cmk --help` for valid options)\n"
    )


def test_the_rejection_names_the_program_as_it_was_called() -> None:
    parsed = _parse(["/omd/sites/mysite/bin/check_mk", "--not-an-option"])

    assert isinstance(parsed, CLIInvalidArguments)
    assert "see `check_mk --help`" in parsed.message


@pytest.mark.parametrize("option", CLI_GENERAL_OPTIONS, ids=lambda option: option.long)
def test_a_general_option_does_not_select_a_command(option: CLIDeclaration) -> None:
    parsed = _parse(["cmk", *_general_option_argv(option), "myhost"])

    assert isinstance(parsed, CLIRunCommand)
    assert parsed.command is _DEFAULT


@pytest.mark.parametrize("option", CLI_GENERAL_OPTIONS, ids=lambda option: option.long)
def test_a_general_option_is_handed_back_for_processing(option: CLIDeclaration) -> None:
    parsed = _parse(["cmk", *_general_option_argv(option), "myhost"])

    assert isinstance(parsed, CLIRunCommand)
    assert f"--{option.long}" in [name for name, _argument in parsed.options]
