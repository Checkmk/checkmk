# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from pathlib import Path

from qemu_windows.tier import read_list, wrapper


def test_calls_a_cmd_script_with_its_args() -> None:
    task = wrapper("bzl-reg-1-2", "run-suite.cmd", ["regression"], {})

    assert task.splitlines()[-1] == r'call "C:\bzl-reg-1-2\run-suite.cmd" regression'


def test_runs_a_ps1_script_with_windows_powershell() -> None:
    task = wrapper("bzl-msi-1-2", "scripts/run.ps1", ["-Code", "X"], {})

    assert task.splitlines()[-1] == (
        "powershell -NoProfile -NonInteractive -ExecutionPolicy Bypass"
        r' -File "C:\bzl-msi-1-2\scripts\run.ps1" -Code X'
    )


def test_sets_env_after_the_guest_directory_it_may_refer_to() -> None:
    lines = wrapper("bzl-reg-1-2", "run.cmd", [], {"BASE": r"%QEMU_GDIR%\base"}).splitlines()

    assert lines.index(r'set "BASE=%QEMU_GDIR%\base"') > lines.index(
        r'set "QEMU_GDIR=C:\bzl-reg-1-2"'
    )


def test_quotes_env_values_so_cmd_exe_metacharacters_stay_literal() -> None:
    lines = wrapper("bzl-int-1-2", "run.cmd", [], {"CMK_VERSION": "2.5.0 & co"}).splitlines()

    assert 'set "CMK_VERSION=2.5.0 & co"' in lines


def test_has_the_crlf_line_ends_cmd_exe_needs() -> None:
    task = wrapper("bzl-reg-1-2", "run.cmd", [], {"BASE": "x"})

    assert task.count("\r\n") == task.count("\n") > 0


def test_list_files_drop_comments_blanks_and_whitespace(tmp_path: Path) -> None:
    path = tmp_path / "excluded.txt"
    path.write_bytes(b"# why\r\n\r\n  Test.One \r\n#Test.Two\nTest.Three\n")

    assert read_list(path) == ["Test.One", "Test.Three"]


def test_comment_only_list_file_is_empty(tmp_path: Path) -> None:
    path = tmp_path / "excluded.txt"
    path.write_text("# nothing excluded\n")

    assert not read_list(path)
