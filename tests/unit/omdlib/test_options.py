#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import pytest

from omdlib.options import (
    _get_command,
    _parse_command_options,
    parse_args_or_exec_other_omd,
)
from omdlib.update_check import prepare_conflict_resolution


def test_parse_args_or_exec_other_omd() -> None:
    arguments = ["create", "--reuse", "foo"]
    _, _, _, command_options, parsed_args = parse_args_or_exec_other_omd(arguments)
    assert "reuse" in command_options
    assert parsed_args == ["foo"]


@pytest.mark.parametrize(
    "arguments, expected_output, expected_rc",
    [
        # No arguments should produce help output
        (
            [],
            "Manage multiple monitoring sites comfortably with OMD. The Open Monitoring Distribution.\nUsage (called as site user):",
            1,
        ),
        # Test both -h and --help work and are position independent
        (["create", "--help"], "Possible options for this command", 0),
        (["create", "-h"], "Possible options for this command", 0),
        (["create", "foo", "-h"], "Possible options for this command", 0),
        # Test invalid option on exemplar 'omd create --foo bar'
        (["create", "--foo", "bar"], "", "Invalid option '--foo'"),
    ],
)
def test_parse_args_or_exec_other_omd_help_argument_position(
    arguments: list[str],
    expected_output: str,
    expected_rc: int | str,
    capsys: pytest.CaptureFixture[str],
) -> None:
    with pytest.raises(SystemExit) as pytest_wrapped_e:
        parse_args_or_exec_other_omd(arguments)
    stdout = capsys.readouterr()[0]
    assert expected_output in stdout
    assert pytest_wrapped_e.value.code == expected_rc


@pytest.mark.parametrize(
    "arguments, expected_command_options, expected_parsed_args, needs_site",
    [
        # Basic test for omd argument handling on exemplar 'omd create foo --reuse'
        (
            ["create", "--reuse", "foo"],
            ["reuse"],
            ["foo"],
            True,
        ),
        # Test parsing of redundant arguments
        (["create", "-n", "-n", "foo"], ["no-init"], ["foo"], True),
        (["help"], [], [], False),
        # Extra argument for 'omd help'
        (["help", "foo"], [], ["foo"], False),
    ],
)
def test_parse_args_or_exec_other_omd_arg_parsing(
    arguments: list[str],
    expected_command_options: list[str],
    expected_parsed_args: list[str],
    needs_site: bool,
) -> None:
    _, _, command, command_options, parsed_args = parse_args_or_exec_other_omd(arguments)
    assert expected_command_options == list(command_options.keys())
    assert all(expected in command_options for expected in expected_command_options)
    assert all(expected in parsed_args for expected in expected_parsed_args)
    assert command.needs_site == needs_site


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
