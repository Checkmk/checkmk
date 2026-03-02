#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from pathlib import Path

import pytest

import omdlib
from omdlib.global_options import GlobalOptions
from omdlib.options import (
    _get_command,
    _parse_command_options,
    ExecOtherOmd,
    parse_args_or_exec_other_omd,
    Root,
    Run,
    SuCommand,
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


@pytest.mark.parametrize(
    "user, args, expected",
    [
        (
            Root(),
            ["create", "monitoring_prod"],
            Run(
                "monitoring_prod",
                GlobalOptions(version=None, verbose=False, force=False),
                _get_command("create"),
                {},
                [],
            ),
        ),
        (
            Root(),
            ["init", "monitoring_prod"],
            Run(
                "monitoring_prod",
                GlobalOptions(version=None, verbose=False, force=False),
                _get_command("init"),
                {},
                [],
            ),
        ),
        (
            Root(),
            ["rm", "monitoring_test"],
            Run(
                "monitoring_test",
                GlobalOptions(version=None, verbose=False, force=False),
                _get_command("rm"),
                {},
                [],
            ),
        ),
        (
            Root(),
            ["disable", "old_site"],
            Run(
                "old_site",
                GlobalOptions(version=None, verbose=False, force=False),
                _get_command("disable"),
                {},
                [],
            ),
        ),
        (
            Root(),
            ["enable", "old_site"],
            Run(
                "old_site",
                GlobalOptions(version=None, verbose=False, force=False),
                _get_command("enable"),
                {},
                [],
            ),
        ),
        (
            Root(),
            ["mv", "site_a", "site_b"],
            Run(
                "site_a",
                GlobalOptions(version=None, verbose=False, force=False),
                _get_command("mv"),
                {},
                ["site_b"],
            ),
        ),
        (
            Root(),
            ["cp", "monitoring_prod", "monitoring_clone"],
            Run(
                "monitoring_prod",
                GlobalOptions(version=None, verbose=False, force=False),
                _get_command("cp"),
                {},
                ["monitoring_clone"],
            ),
        ),
        (
            Root(),
            ["su", "monitoring_prod"],
            SuCommand(target_site="monitoring_prod"),
        ),
        (
            Root(),
            ["setversion", "2.2.0p9.cre"],
            Run(
                None,
                GlobalOptions(version=None, verbose=False, force=False),
                _get_command("setversion"),
                {},
                ["2.2.0p9.cre"],
            ),
        ),
        (
            Root(),
            ["cleanup"],
            Run(
                None,
                GlobalOptions(version=None, verbose=False, force=False),
                _get_command("cleanup"),
                {},
                [],
            ),
        ),
        (
            Root(),
            ["start", "monitoring_prod"],
            Run(
                "monitoring_prod",
                GlobalOptions(version=None, verbose=False, force=False),
                _get_command("start"),
                {},
                [],
            ),
        ),
        (
            Root(),
            ["restart", "monitoring_prod", "apache"],
            Run(
                "monitoring_prod",
                GlobalOptions(version=None, verbose=False, force=False),
                _get_command("restart"),
                {},
                ["apache"],
            ),
        ),
        (
            Root(),
            ["status", "monitoring_prod"],
            Run(
                "monitoring_prod",
                GlobalOptions(version=None, verbose=False, force=False),
                _get_command("status"),
                {},
                [],
            ),
        ),
        (
            Root(),
            ["start", "--version", "abc", "-p"],
            Run(
                None,
                GlobalOptions(version=None, verbose=False, force=False),
                _get_command("start"),
                {"parallel": None, "version": "abc"},
                [],
            ),
        ),
        (
            Root(),
            ["backup", "monitoring_prod", "/tmp/prod_backup.tar.gz"],
            Run(
                "monitoring_prod",
                GlobalOptions(version=None, verbose=False, force=False),
                _get_command("backup"),
                {},
                ["/tmp/prod_backup.tar.gz"],
            ),
        ),
        (
            "v250",
            ["start"],
            Run(
                "v250",
                GlobalOptions(version=None, verbose=False, force=False),
                _get_command("start"),
                {},
                [],
            ),
        ),
        (
            "v250",
            ["start", "apache"],
            Run(
                "v250",
                GlobalOptions(version=None, verbose=False, force=False),
                _get_command("start"),
                {},
                ["apache"],
            ),
        ),
        (
            "v250",
            ["stop"],
            Run(
                "v250",
                GlobalOptions(version=None, verbose=False, force=False),
                _get_command("stop"),
                {},
                [],
            ),
        ),
        (
            "v250",
            ["restart"],
            Run(
                "v250",
                GlobalOptions(version=None, verbose=False, force=False),
                _get_command("restart"),
                {},
                [],
            ),
        ),
        (
            "v250",
            ["reload", "apache"],
            Run(
                "v250",
                GlobalOptions(version=None, verbose=False, force=False),
                _get_command("reload"),
                {},
                ["apache"],
            ),
        ),
        (
            "v250",
            ["status"],
            Run(
                "v250",
                GlobalOptions(version=None, verbose=False, force=False),
                _get_command("status"),
                {},
                [],
            ),
        ),
        (
            "v250",
            ["version"],
            Run(
                None,
                GlobalOptions(version=None, verbose=False, force=False),
                _get_command("version"),
                {},
                [],
            ),
        ),
        (
            "v250",
            ["versions"],
            Run(
                None,
                GlobalOptions(version=None, verbose=False, force=False),
                _get_command("versions"),
                {},
                [],
            ),
        ),
        (
            "v250",
            ["sites"],
            Run(
                None,
                GlobalOptions(version=None, verbose=False, force=False),
                _get_command("sites"),
                {},
                [],
            ),
        ),
        (
            "v250",
            ["update"],
            Run(
                "v250",
                GlobalOptions(version=None, verbose=False, force=False),
                _get_command("update"),
                {},
                [],
            ),
        ),
        (
            "v250",
            ["config"],
            Run(
                "v250",
                GlobalOptions(version=None, verbose=False, force=False),
                _get_command("config"),
                {},
                [],
            ),
        ),
        (
            "v250",
            ["config", "show"],
            Run(
                "v250",
                GlobalOptions(version=None, verbose=False, force=False),
                _get_command("config"),
                {},
                ["show"],
            ),
        ),
        (
            "v250",
            ["config", "set", "CORE", "cmc"],
            Run(
                "v250",
                GlobalOptions(version=None, verbose=False, force=False),
                _get_command("config"),
                {},
                ["set", "CORE", "cmc"],
            ),
        ),
        (
            "v250",
            ["diff"],
            Run(
                "v250",
                GlobalOptions(version=None, verbose=False, force=False),
                _get_command("diff"),
                {},
                [],
            ),
        ),
        (
            "v250",
            ["backup", "/tmp/site_backup.tar.gz"],
            Run(
                "v250",
                GlobalOptions(version=None, verbose=False, force=False),
                _get_command("backup"),
                {},
                ["/tmp/site_backup.tar.gz"],
            ),
        ),
        (
            "v250",
            ["-V", "2.2.0p10.cre", "create", "new_site"],
            ExecOtherOmd(version="2.2.0p10.cre"),
        ),
        (
            "v250",
            ["-V", "2.1.0p30.cre", "update", "existing_site"],
            ExecOtherOmd(version="2.1.0p30.cre"),
        ),
        (
            "v250",
            ["-f", "update", "stubborn_site"],
            Run(
                "v250",
                GlobalOptions(version=None, verbose=False, force=True),
                _get_command("update"),
                {},
                ["stubborn_site"],
            ),
        ),
        (
            "v250",
            ["-f", "update"],
            Run(
                "v250",
                GlobalOptions(version=None, verbose=False, force=True),
                _get_command("update"),
                {},
                [],
            ),
        ),
        (
            "v250",
            ["--force", "update"],
            Run(
                "v250",
                GlobalOptions(version=None, verbose=False, force=True),
                _get_command("update"),
                {},
                [],
            ),
        ),
    ],
)
def test_parse_args_or_exec_other_omd(
    user: str, args: list[str], tmp_path: Path, expected: Run | ExecOtherOmd
) -> None:
    # Programmatically create the site directory and symlink to prevent sys.exit
    for site in ["old_site", "v250", "monitoring_prod", "monitoring_test", "site_a"]:
        site_dir = tmp_path / "sites" / site
        site_dir.mkdir(parents=True, exist_ok=True)
        (site_dir / "version").symlink_to(omdlib.__version__)

    assert parse_args_or_exec_other_omd(user, args, tmp_path) == expected


@pytest.mark.parametrize(
    "user, args, expected_output, expected_rc",
    [
        # 1. No arguments provided
        (
            Root(),
            [],
            "Manage multiple monitoring sites comfortably",  # Fits both root and site-user outputs
            1,
        ),
        # 2. Invalid command provided (calls main_help() which prints to stdout)
        (
            Root(),
            ["does_not_exist"],
            "Manage multiple monitoring sites comfortably",
            1,
        ),
        # 3. Missing required site name
        (
            Root(),
            ["create"],
            "",
            "omd: please specify site.",
        ),
        # 4. Command help flag (exits cleanly with 0)
        (
            Root(),
            ["create", "--help"],
            "Create a new site (-u UID, -g GID)",
            0,
        ),
        # 5. Target site does not exist
        (
            Root(),
            ["start", "ghost_site"],
            "",
            "omd: The site 'ghost_site' does not exist. You need to execute omd as root or site user.",
        ),
        # 6. Invalid option flag provided (Flags must come BEFORE positional args)
        (
            Root(),
            ["create", "--invalid-flag", "mysite"],
            "",
            "Invalid option '--invalid-flag'",
        ),
        # 7. Option provided but missing its required argument (Flags must come BEFORE positional args)
        (
            Root(),
            ["create", "--uid"],
            "",
            "Option '--uid' needs an argument.",
        ),
        # 8. Command requiring version on a broken site
        (
            Root(),
            ["start", "broken_site"],
            "",
            "This site has an empty home directory /omd/sites/broken_site.\n"
            "If you have created that site with 'omd create --no-init broken_site'\n"
            "then please first do an 'omd init broken_site'.",
        ),
        # 9. Command requiring version on a broken site as user
        (
            "broken_site",
            ["start"],
            "",
            "This site has an empty home directory /omd/sites/broken_site.\n"
            "If you have created that site with 'omd create --no-init broken_site'\n"
            "then please first do an 'omd init broken_site'.",
        ),
        # 10. Command requires root permission
        (
            "v250",
            ["--force", "rm", "broken_site"],
            "",
            "omd: root permissions are needed for this command.",
        ),
        (
            "v250",
            ["cleanup"],
            "",
            "omd: root permissions are needed for this command.",
        ),
        (
            "v250",
            ["su", "abc"],
            "",
            "omd: root permissions are needed for this command.",
        ),
    ],
)
def test_parse_args_or_exec_other_omd_error(
    user: str | Root,
    args: list[str],
    expected_output: str,
    expected_rc: int | str,
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    site_dir = tmp_path / "sites" / "broken_site"
    site_dir.mkdir(parents=True)  # No 'version' symlink created
    site_dir = tmp_path / "sites" / "v250"
    site_dir.mkdir(parents=True, exist_ok=True)
    (site_dir / "version").symlink_to(omdlib.__version__)
    with pytest.raises(SystemExit) as pytest_wrapped_e:
        parse_args_or_exec_other_omd(user, args, tmp_path)
    stdout = capsys.readouterr()[0]
    assert expected_output in stdout
    assert pytest_wrapped_e.value.code == expected_rc


def test_parse_args_or_exec_other_omd_no_version_link_rm_warns(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    site_dir = tmp_path / "sites" / "broken_site"
    site_dir.mkdir(parents=True)  # No 'version' symlink created

    result = parse_args_or_exec_other_omd(Root(), ["rm", "broken_site"], tmp_path)
    assert isinstance(result, Run)
    assert result.site_name == "broken_site"
    assert "WARNING: This site has an empty home directory" in capsys.readouterr().out


def test_parse_args_or_exec_other_omd_use_site_version(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    site_dir = tmp_path / "sites" / "v250"
    site_dir.mkdir(parents=True)
    (site_dir / "version").symlink_to("abc")

    result = parse_args_or_exec_other_omd(Root(), ["rm", "v250"], tmp_path)
    assert result == ExecOtherOmd(version="abc")
