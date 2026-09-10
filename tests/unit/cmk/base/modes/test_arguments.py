#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Sequence
from typing import Final

import pytest

from cmk.base.modes.arguments import InvalidArguments, parse, RunMode, ShowHelp
from cmk.base.modes.check_mk import general_options
from cmk.base.modes.modes import discover_modes, Mode, Modes, Option
from cmk.checkengine.plugins import CheckPluginName

_MODES: Final = Modes(plugins=discover_modes(), general_options=general_options())

_MODE_ARGUMENT: Final = "myhost"

_ARGUMENT_EVERY_CONVERSION_ACCEPTS: Final = "inline"


def _mode_argv(mode: Mode, option: str) -> Sequence[str]:
    if not mode.argument or mode.argument_optional:
        return [option]
    if option.startswith("--"):
        return [f"{option}={_MODE_ARGUMENT}"]
    return [option, _MODE_ARGUMENT]


def _sub_option_argv(option: Option) -> Sequence[str]:
    if option.takes_argument():
        return [f"--{option.long_option}={_ARGUMENT_EVERY_CONVERSION_ACCEPTS}"]
    return [f"--{option.long_option}"]


def _short_sub_option_argv(option: Option) -> Sequence[str]:
    if option.takes_argument():
        return [f"-{option.short_option}", _ARGUMENT_EVERY_CONVERSION_ACCEPTS]
    return [f"-{option.short_option}"]


@pytest.mark.parametrize("mode", discover_modes(), ids=lambda mode: mode.name)
def test_the_long_option_selects_its_mode(mode: Mode) -> None:
    parsed = parse(_MODES, ["cmk", *_mode_argv(mode, f"--{mode.long_option}")])

    assert isinstance(parsed, RunMode)
    assert parsed.mode is mode


@pytest.mark.parametrize(
    "mode",
    [mode for mode in discover_modes() if mode.short_option is not None],
    ids=lambda mode: mode.name,
)
def test_the_short_option_selects_its_mode(mode: Mode) -> None:
    parsed = parse(_MODES, ["cmk", *_mode_argv(mode, f"-{mode.short_option}")])

    assert isinstance(parsed, RunMode)
    assert parsed.mode is mode


@pytest.mark.parametrize(
    ("mode", "option"),
    [(mode, option) for mode in discover_modes() for option in mode.sub_options],
    ids=lambda value: value.name,
)
def test_every_sub_option_reaches_its_mode(mode: Mode, option: Option) -> None:
    parsed = parse(
        _MODES,
        ["cmk", *_mode_argv(mode, f"--{mode.long_option}"), *_sub_option_argv(option)],
    )

    assert isinstance(parsed, RunMode)
    assert option.name in (parsed.mode.get_sub_options(parsed.options) or {})


@pytest.mark.parametrize(
    ("mode", "option"),
    [
        (mode, option)
        for mode in discover_modes()
        for option in mode.sub_options
        if option.short_option is not None
    ],
    ids=lambda value: value.name,
)
def test_every_short_sub_option_reaches_its_mode(mode: Mode, option: Option) -> None:
    parsed = parse(
        _MODES,
        ["cmk", *_mode_argv(mode, f"--{mode.long_option}"), *_short_sub_option_argv(option)],
    )

    assert isinstance(parsed, RunMode)
    assert option.name in (parsed.mode.get_sub_options(parsed.options) or {})


def test_a_bare_command_shows_the_help() -> None:
    assert parse(_MODES, ["cmk"]) == ShowHelp(options=[])


def test_a_general_option_alone_shows_the_help_and_hands_the_options_back() -> None:
    assert parse(_MODES, ["cmk", "-v"]) == ShowHelp(options=[("-v", "")])


@pytest.mark.parametrize("option", ["--help", "-h"])
def test_the_help_option_selects_the_help_mode(option: str) -> None:
    parsed = parse(_MODES, ["cmk", option])

    assert isinstance(parsed, RunMode)
    assert parsed.mode.name == "help"


def test_the_first_of_two_mode_options_wins() -> None:
    parsed = parse(_MODES, ["cmk", "--version", "--list-checks"])

    assert isinstance(parsed, RunMode)
    assert parsed.mode.name == "version"


def test_a_required_mode_argument_comes_off_the_option() -> None:
    parsed = parse(_MODES, ["cmk", "--dump-agent=myhost"])

    assert isinstance(parsed, RunMode)
    assert (parsed.argument, parsed.arguments) == ("myhost", [])


def test_an_optional_mode_argument_stays_in_the_positional_arguments() -> None:
    parsed = parse(_MODES, ["cmk", "--inventory", "host1", "host2"])

    assert isinstance(parsed, RunMode)
    assert (parsed.argument, parsed.arguments) == ("", ["host1", "host2"])


def test_a_repeated_sub_option_is_counted() -> None:
    parsed = parse(_MODES, ["cmk", "-II", "myhost"])

    assert isinstance(parsed, RunMode)
    assert parsed.mode.get_sub_options(parsed.options) == {"discover": 2}


def test_a_sub_option_argument_is_converted() -> None:
    parsed = parse(_MODES, ["cmk", "--check", "--plugins=cpu", "myhost"])

    assert isinstance(parsed, RunMode)
    assert parsed.mode.get_sub_options(parsed.options) == {"plugins": {CheckPluginName("cpu")}}


def test_a_deprecated_sub_option_reaches_the_option_it_replaces() -> None:
    parsed = parse(_MODES, ["cmk", "--check", "--checks=cpu", "myhost"])

    assert isinstance(parsed, RunMode)
    assert parsed.mode.get_sub_options(parsed.options) == {"detect-plugins": {"cpu"}}


def test_one_argument_runs_the_implicit_check_mode() -> None:
    parsed = parse(_MODES, ["cmk", "myhost"])

    assert isinstance(parsed, RunMode)
    assert (parsed.mode.name, parsed.argument, parsed.arguments) == ("check", None, ["myhost"])


def test_a_host_and_an_address_run_the_implicit_check_mode() -> None:
    parsed = parse(_MODES, ["cmk", "myhost", "1.2.3.4"])

    assert isinstance(parsed, RunMode)
    assert (parsed.mode.name, parsed.arguments) == ("check", ["myhost", "1.2.3.4"])


def test_keepalive_runs_the_implicit_check_mode() -> None:
    parsed = parse(_MODES, ["cmk", "--keepalive"])

    assert isinstance(parsed, RunMode)
    assert parsed.mode.name == "check"


def test_more_arguments_than_a_host_and_an_address_show_the_help() -> None:
    parsed = parse(_MODES, ["cmk", "host1", "host2", "host3"])

    assert isinstance(parsed, ShowHelp)


def test_an_unknown_option_is_rejected() -> None:
    parsed = parse(_MODES, ["cmk", "--not-an-option"])

    assert parsed == InvalidArguments(
        "ERROR: option --not-an-option not recognized (see `cmk --help` for valid options)\n"
    )


def test_a_missing_mode_argument_is_rejected() -> None:
    parsed = parse(_MODES, ["cmk", "--dump-agent"])

    assert parsed == InvalidArguments(
        "ERROR: option --dump-agent requires argument (see `cmk --help` for valid options)\n"
    )


def test_the_rejection_names_the_program_as_it_was_called() -> None:
    parsed = parse(_MODES, ["/omd/sites/mysite/bin/check_mk", "--not-an-option"])

    assert isinstance(parsed, InvalidArguments)
    assert "see `check_mk --help`" in parsed.message
