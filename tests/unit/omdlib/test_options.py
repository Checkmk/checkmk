#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import pytest

from omdlib.options import (
    _get_command,
    _parse_command_options,
)
from omdlib.update_check import prepare_conflict_resolution


@pytest.mark.parametrize(
    "arguments, expected_output, expected_rc",
    [
        # Test both -h and --help work and are position independent
        (["--help"], "Possible options for this command", 0),
        (["-h"], "Possible options for this command", 0),
        (["foo", "-h"], "Possible options for this command", 0),
        # Test invalid option on exemplar 'omd create --foo bar'
        (["--foo", "bar"], "", "Invalid option '--foo'"),
    ],
)
def test_parse_command_options_help_argument_position(
    arguments: list[str],
    expected_output: str,
    expected_rc: int | str,
    capsys: pytest.CaptureFixture[str],
) -> None:
    command = _get_command("create")
    with pytest.raises(SystemExit) as pytest_wrapped_e:
        args, options = _parse_command_options(command.description, arguments, command.options)
    stdout = capsys.readouterr()[0]
    assert expected_output in stdout
    assert pytest_wrapped_e.value.code == expected_rc


@pytest.mark.parametrize(
    "arguments, expected_command_options, expected_parsed_args",
    [
        # Basic test for omd argument handling on exemplar 'omd create foo --reuse'
        (
            ["--reuse", "foo"],
            {"reuse": None},
            ["foo"],
        ),
        # Test parsing of redundant arguments
        (
            ["-n", "-n", "foo"],
            {"no-init": None},
            ["foo"],
        ),
    ],
)
def test_parse_command_options_create(
    arguments: list[str],
    expected_command_options: dict[str, object],
    expected_parsed_args: list[str],
) -> None:
    command = _get_command("create")
    args, options = _parse_command_options(command.description, arguments, command.options)
    assert args == expected_parsed_args
    assert options == expected_command_options


@pytest.mark.parametrize(
    "arguments, expected_command_options, expected_parsed_args",
    [
        ([], {}, []),
        # Extra argument for 'omd help'
        (["foo"], {}, ["foo"]),
    ],
)
def test_parse_command_options_help(
    arguments: list[str],
    expected_command_options: dict[str, object],
    expected_parsed_args: list[str],
) -> None:
    command = _get_command("help")
    args, options = _parse_command_options(command.description, arguments, command.options)
    assert args == expected_parsed_args
    assert options == expected_command_options


def test_parse_command_options_update() -> None:
    command = _get_command("update")
    args, options = _parse_command_options(
        command.description,
        [
            "--confirm-version",
            "--confirm-edition",
            "--ignore-editions-incompatible",
            "--confirm-requires-root",
            "--ignore-versions-incompatible",
        ],
        command.options,
    )
    assert not args
    prepare_conflict_resolution(options, False)


def test_parse_command_options_update_incorrect_usage() -> None:
    command = _get_command("update")
    with pytest.raises(SystemExit):
        _parse_command_options(command.description, ["--confirm-choice"], command.options)


def test_parse_command_options_update_force() -> None:
    command = _get_command("update")
    args, options = _parse_command_options(command.description, [], command.options)
    assert not args
    prepare_conflict_resolution(options, True)


def test_parse_command_options_update_default() -> None:
    command = _get_command("update")
    args, options = _parse_command_options(command.description, [], command.options)
    assert not args
    prepare_conflict_resolution(options, False)
