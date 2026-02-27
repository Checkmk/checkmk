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
        (["-u"], "", "Option '-u' needs an argument."),
        (["--uid"], "", "Option '--uid' needs an argument."),
        (["-t"], "", "Option '-t' needs an argument."),
        (["--tmpfs-size"], "", "Option '--tmpfs-size' needs an argument."),
        # Test boolean options incorrectly given an argument
        (["--reuse=blah"], "", "The option --reuse does not take an argument"),
        (["--reuse="], "", "The option --reuse does not take an argument"),
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
        # Basic test for boolean flag
        (
            ["--reuse", "foo"],
            {"reuse": None},
            ["foo"],
        ),
        # Test another boolean flag
        (
            ["--kill", "foo"],
            {"kill": None},
            ["foo"],
        ),
        # Test flag with an argument (conflict resolution)
        (
            ["--conflict=install", "foo"],
            {"conflict": "install"},
            ["foo"],
        ),
        # Test short flag with argument (UID)
        (
            ["-u", "1000", "foo"],
            {"uid": "1000"},
            ["foo"],
        ),
        # Test long flag with argument (GID)
        (
            ["--gid", "2000", "foo"],
            {"gid": "2000"},
            ["foo"],
        ),
        # Test short flag with argument (TMPFS)
        (
            ["-t", "500M", "foo"],
            {"tmpfs-size": "500M"},
            ["foo"],
        ),
        # Test apache-reload flag
        (
            ["--apache-reload", "foo"],
            {"apache-reload": None},
            ["foo"],
        ),
        # Test parsing of redundant boolean arguments
        (
            ["--kill", "--kill", "foo"],
            {"kill": None},
            ["foo"],
        ),
        # Test combined boolean and value arguments
        (
            ["--reuse", "--conflict", "keepold", "-t", "60%", "foo", "backup.tar.gz"],
            {"reuse": None, "conflict": "keepold", "tmpfs-size": "60%"},
            ["foo", "backup.tar.gz"],
        ),
    ],
)
def test_parse_command_options_restore(
    arguments: list[str],
    expected_command_options: dict[str, object],
    expected_parsed_args: list[str],
) -> None:
    command = _get_command("restore")
    args, options = _parse_command_options(command.description, arguments, command.options)
    assert args == expected_parsed_args
    assert options == expected_command_options


@pytest.mark.parametrize(
    "arguments, expected_command_options, expected_parsed_args",
    [
        # Test combined boolean and value arguments
        (
            ["--no-agents", "-"],
            {"no-agents": None},
            ["-"],
        ),
    ],
)
def test_parse_command_options_backup(
    arguments: list[str],
    expected_command_options: dict[str, object],
    expected_parsed_args: list[str],
) -> None:
    command = _get_command("backup")
    args, options = _parse_command_options(command.description, arguments, command.options)
    assert args == expected_parsed_args
    assert options == expected_command_options


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
        # Test short flag with argument (UID)
        (
            ["-u", "1000", "foo"],
            {"uid": "1000"},
            ["foo"],
        ),
        # Test long flag with argument (GID)
        (
            ["--gid", "2000", "foo"],
            {"gid": "2000"},
            ["foo"],
        ),
        # Test long flag with '=' syntax for arguments
        (
            ["--admin-password=supersecret", "foo"],
            {"admin-password": "supersecret"},
            ["foo"],
        ),
        # Test long flag with space syntax for arguments
        (
            ["--admin-password", "supersecret", "foo"],
            {"admin-password": "supersecret"},
            ["foo"],
        ),
        # Test short flag for tmpfs size
        (
            ["-t", "500M", "foo"],
            {"tmpfs-size": "500M"},
            ["foo"],
        ),
        # Test boolean short flag
        (
            ["-A", "foo"],
            {"no-autostart": None},
            ["foo"],
        ),
        # Test boolean long flags
        (
            ["--no-tmpfs", "foo"],
            {"no-tmpfs": None},
            ["foo"],
        ),
        (
            ["--apache-reload", "foo"],
            {"apache-reload": None},
            ["foo"],
        ),
        # Test combined flags and arguments
        (
            ["-u", "1001", "-A", "--admin-password=pass", "--tmpfs-size", "20G", "foo"],
            {"uid": "1001", "no-autostart": None, "admin-password": "pass", "tmpfs-size": "20G"},
            ["foo"],
        ),
        # Test multiple grouped boolean flags
        (
            ["-nA", "foo"],
            {"no-init": None, "no-autostart": None},
            ["foo"],
        ),
        # Test multiple grouped booleans ending with a flag requiring an argument
        (
            ["-nAu", "1002", "foo"],
            {"no-init": None, "no-autostart": None, "uid": "1002"},
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
