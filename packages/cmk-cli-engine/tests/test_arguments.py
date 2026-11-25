#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Sequence
from pathlib import Path
from typing import Final, NoReturn

import pytest

from cmk.cli.engine.arguments import _Deprecation as CLIDeprecation
from cmk.cli.engine.arguments import InvalidArguments as CLIInvalidArguments
from cmk.cli.engine.arguments import parse as cli_parse
from cmk.cli.engine.arguments import RunCommand as CLIRunCommand
from cmk.cli.engine.arguments import ShowHelp as CLIShowHelp
from cmk.cli.engine.commands import Commands as CLICommands
from cmk.cli.engine.options import ENGINE_OPTIONS as CLI_ENGINE_OPTIONS
from cmk.cli.engine.options import GlobalOptions as CLIEngineGlobalOptions
from cmk.cli.engine.options import HELP_OPTION as CLI_HELP_OPTION
from cmk.cli.engine.options import Option as CLIOption
from cmk.cli.engine.options import placeholder as cli_placeholder
from cmk.cli.internal import Argument as CLIArgument
from cmk.cli.internal import Arguments as CLIArguments
from cmk.cli.internal import Command as CLICommand
from cmk.cli.internal import Context as CLIContext
from cmk.cli.internal import Count as CLICount
from cmk.cli.internal import ExitCode as CLIExitCode
from cmk.cli.internal import Flag as CLIFlag
from cmk.cli.internal import no_options as cli_no_options
from cmk.cli.internal import OptionalArgument as CLIOptionalArgument
from cmk.cli.internal import Reader as CLIReader
from cmk.cli.internal import Value as CLIValue
from cmk.cli.internal import Values as CLIValues

from ._commands import command_with, HANDED_IN


def _unreachable(_context: CLIContext, _request: object) -> NoReturn:
    raise AssertionError("parsing must not run the command")


_COMMAND_ARGUMENT: Final = "myhost"

_ARGUMENT_EVERY_CONVERSION_ACCEPTS: Final = "inline"

_PLAIN: Final = command_with(
    CLICommand(
        name="plain",
        handler=HANDED_IN,
        long="plain",
        short="p",
        request=cli_no_options,
        help="takes no argument",
    ),
    _unreachable,
)

_OTHER_PLAIN: Final = command_with(
    CLICommand(
        name="other_plain",
        handler=HANDED_IN,
        long="other-plain",
        request=cli_no_options,
        help="takes no argument either",
    ),
    _unreachable,
)


def _host_request(options: CLIReader) -> str | None:
    return options.argument(CLIArgument(placeholder="HOST", parse=str))


_WITH_ARGUMENT: Final = command_with(
    CLICommand(
        name="with_argument",
        handler=HANDED_IN,
        long="with-argument",
        request=_host_request,
        help="needs exactly one argument",
    ),
    _unreachable,
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

_NUMBERED_VALUE: Final = CLIValue(
    long="numbered",
    short="n",
    placeholder="N",
    help="takes an argument by its short spelling",
    parse=int,
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
) -> tuple[bool, int, Sequence[str], int | None, str | None, Sequence[str]]:
    return (
        options.flag(_FLAG),
        options.count(_COUNTED_COUNT),
        options.values(_COLLECTED_VALUES),
        options.value(_NUMBERED_VALUE),
        options.value(_RENAMED_VALUE),
        options.arguments(CLIArguments(placeholder="HOSTS", parse=str)),
    )


_DEFAULT: Final = command_with(
    CLICommand(
        name="default",
        handler=HANDED_IN,
        long="default",
        short="c",
        request=_default_request,
        default=True,
        help="the default command",
    ),
    lambda *_args: CLIExitCode.SUCCESS,
)


def _pair_request(options: CLIReader) -> tuple[str | None, str | None]:
    return (
        options.argument(CLIArgument(placeholder="HOST", parse=str)),
        options.argument(CLIOptionalArgument(placeholder="ADDRESS", parse=str)),
    )


_PAIR: Final = command_with(
    CLICommand(
        name="pair",
        handler=HANDED_IN,
        long="pair",
        request=_pair_request,
        help="needs a host and takes an address",
    ),
    _unreachable,
)

_COMMANDS: Final = CLICommands(commands=[_PLAIN, _OTHER_PLAIN, _WITH_ARGUMENT, _PAIR, _DEFAULT])


_GENERAL_OPTIONS: Final = [option for option in CLI_ENGINE_OPTIONS if option is not CLI_HELP_OPTION]


def _parse(argv: Sequence[str]) -> CLIRunCommand | CLIShowHelp | CLIInvalidArguments:
    return cli_parse(_COMMANDS, argv)


def _general_option_argv(option: CLIOption) -> Sequence[str]:
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
    assert parsed.bound.request == (True, 0, (), None, None, ())


def test_every_spelling_of_a_counted_option_counts() -> None:
    parsed = _parse(["cmk", "--default", "--counted", "-c", "myhost"])

    assert isinstance(parsed, CLIRunCommand)
    assert parsed.bound.request == (False, 2, (), None, None, ("myhost",))


def test_an_optional_argument_left_out_reads_none() -> None:
    parsed = _parse(["cmk", "--pair", "myhost"])

    assert isinstance(parsed, CLIRunCommand)
    assert parsed.bound.request == ("myhost", None)


def test_a_bare_command_shows_the_help() -> None:
    assert _parse(["cmk"]) == CLIShowHelp(CLIEngineGlobalOptions())


def test_a_general_option_alone_shows_the_help_with_the_general_options() -> None:
    assert _parse(["cmk", "-v"]) == CLIShowHelp(CLIEngineGlobalOptions(verbosity=1))


def test_the_verbosity_counts_the_short_and_long_spelling_alike() -> None:
    assert _parse(["cmk", "-v", "--verbose"]) == CLIShowHelp(CLIEngineGlobalOptions(verbosity=2))


def test_the_log_file_is_a_path() -> None:
    assert _parse(["cmk", "--log-file", "var/log/cmk.log"]) == CLIShowHelp(
        CLIEngineGlobalOptions(log_file=Path("var/log/cmk.log"))
    )


def test_a_commands_own_option_is_no_general_option() -> None:
    parsed = _parse(["cmk", "--default", "--flag"])

    assert isinstance(parsed, CLIRunCommand)
    assert parsed.global_options == CLIEngineGlobalOptions()


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
    assert parsed.bound.request == _COMMAND_ARGUMENT


def test_an_optional_command_argument_takes_all_positional_arguments() -> None:
    parsed = _parse(["cmk", "--default", "host1", "host2"])

    assert isinstance(parsed, CLIRunCommand)
    assert parsed.bound.request == (False, 0, (), None, None, ("host1", "host2"))


def test_a_repeated_short_spelling_selects_the_command_and_stays_an_option() -> None:
    parsed = _parse(["cmk", "-cc", "myhost"])

    assert isinstance(parsed, CLIRunCommand)
    assert (parsed.command, parsed.bound.request) == (
        _DEFAULT,
        (False, 2, (), None, None, ("myhost",)),
    )


def test_a_repeated_sub_option_argument_is_kept_every_time() -> None:
    parsed = _parse(["cmk", "--default", "--collected=.1.1", "--collected=.1.2", "myhost"])

    assert isinstance(parsed, CLIRunCommand)
    assert parsed.bound.request == (False, 0, (".1.1", ".1.2"), None, None, ("myhost",))


def test_a_deprecated_sub_option_reaches_its_command() -> None:
    parsed = _parse(["cmk", "--default", "--legacy-name=value", "myhost"])

    assert isinstance(parsed, CLIRunCommand)
    assert parsed.bound.request == (False, 0, (), None, "value", ("myhost",))


def test_a_deprecated_spelling_is_noted_with_its_replacement() -> None:
    parsed = _parse(["cmk", "--default", "--legacy-name=value", "myhost"])

    assert isinstance(parsed, CLIRunCommand)
    assert parsed.deprecations == [CLIDeprecation(spelling="--legacy-name", replacement="renamed")]


def test_a_short_option_takes_the_next_argument_as_its_value() -> None:
    parsed = _parse(["cmk", "--default", "-n", "5", "myhost"])

    assert isinstance(parsed, CLIRunCommand)
    assert parsed.bound.request == (False, 0, (), 5, None, ("myhost",))


def test_positional_arguments_alone_run_the_default_command() -> None:
    parsed = _parse(["cmk", "myhost", "1.2.3.4"])

    assert isinstance(parsed, CLIRunCommand)
    assert (parsed.command, parsed.bound.request) == (
        _DEFAULT,
        (False, 0, (), None, None, ("myhost", "1.2.3.4")),
    )


def test_without_a_default_command_positional_arguments_show_the_help() -> None:
    commands = CLICommands(commands=[_PLAIN])

    assert isinstance(cli_parse(commands, ["cmk", "myhost"]), CLIShowHelp)


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


def test_a_missing_required_argument_is_rejected() -> None:
    assert _parse(["cmk", "--pair"]) == CLIInvalidArguments(
        "ERROR: HOST: Missing argument (see `cmk --help` for valid options)\n"
    )


@pytest.mark.parametrize(
    "argv",
    [
        pytest.param(["cmk", "--pair", "myhost", "1.2.3.4", "surplus"], id="after the last"),
        pytest.param(["cmk", "--plain", "surplus"], id="to a command reading none"),
        pytest.param(["cmk", "--with-argument=myhost", "surplus"], id="after the option value"),
    ],
)
def test_an_argument_no_one_reads_is_rejected(argv: Sequence[str]) -> None:
    assert _parse(argv) == CLIInvalidArguments(
        "ERROR: surplus: Unexpected argument (see `cmk --help` for valid options)\n"
    )


def test_an_option_argument_the_conversion_rejects_is_rejected() -> None:
    parsed = _parse(["cmk", "--default", "--numbered", "x", "myhost"])

    assert isinstance(parsed, CLIInvalidArguments)
    assert "--numbered: Invalid argument 'x'" in parsed.message


def test_the_rejection_names_the_program_as_it_was_called() -> None:
    parsed = _parse(["/omd/sites/mysite/bin/check_mk", "--not-an-option"])

    assert isinstance(parsed, CLIInvalidArguments)
    assert "see `check_mk --help`" in parsed.message


@pytest.mark.parametrize("option", _GENERAL_OPTIONS, ids=lambda option: option.long)
def test_a_general_option_does_not_select_a_command(option: CLIOption) -> None:
    parsed = _parse(["cmk", *_general_option_argv(option), "myhost"])

    assert isinstance(parsed, CLIRunCommand)
    assert parsed.command is _DEFAULT


@pytest.mark.parametrize("option", _GENERAL_OPTIONS, ids=lambda option: option.long)
def test_a_general_option_is_read_into_the_global_options(option: CLIOption) -> None:
    parsed = _parse(["cmk", *_general_option_argv(option), "myhost"])

    assert isinstance(parsed, CLIRunCommand)
    assert parsed.global_options != CLIEngineGlobalOptions()
