# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import stat
from pathlib import Path

from qemu_windows.stage import read_list, Stage


def test_copies_follow_symlinks_like_runfiles(tmp_path: Path) -> None:
    (tmp_path / "real").mkdir()
    (tmp_path / "real/plugin.cmd").write_text("x")
    (tmp_path / "runfiles").mkdir()
    (tmp_path / "runfiles/plugin.cmd").symlink_to(tmp_path / "real/plugin.cmd")
    stage = Stage(tmp_path / "stage")

    stage.add(tmp_path / "runfiles", "plugins")

    copy = tmp_path / "stage/plugins/plugin.cmd"
    assert not copy.is_symlink() and copy.read_text() == "x"


def test_copies_of_read_only_files_are_writable(tmp_path: Path) -> None:
    source = tmp_path / "check_mk.yml"
    source.write_text("x")
    source.chmod(0o444)
    stage = Stage(tmp_path / "stage")

    stage.add(source, "root/check_mk.yml")

    # The mode, not os.access(): root may write to any file.
    assert not source.stat().st_mode & stat.S_IWUSR
    assert (tmp_path / "stage/root/check_mk.yml").stat().st_mode & stat.S_IWUSR


def test_add_files_flattens_and_skips_directories(tmp_path: Path) -> None:
    (tmp_path / "plugins/subdir").mkdir(parents=True)
    (tmp_path / "plugins/a.ps1").write_text("a")
    stage = Stage(tmp_path / "stage")

    stage.add_files((tmp_path / "plugins").iterdir(), "root/plugins")

    assert [p.name for p in (tmp_path / "stage/root/plugins").iterdir()] == ["a.ps1"]


def test_written_guest_scripts_have_crlf_line_ends(tmp_path: Path) -> None:
    stage = Stage(tmp_path)

    stage.write("task.cmd", "@echo off\nexit /b 0\n")

    assert (tmp_path / "task.cmd").read_bytes() == b"@echo off\r\nexit /b 0\r\n"


def test_to_crlf_converts_only_the_given_suffixes(tmp_path: Path) -> None:
    (tmp_path / "files/sub").mkdir(parents=True)
    (tmp_path / "files/sub/a.cmd").write_bytes(b"one\ntwo\r\n")
    (tmp_path / "files/b.exe").write_bytes(b"\n")
    stage = Stage(tmp_path)

    stage.to_crlf("files", (".cmd",))

    assert (tmp_path / "files/sub/a.cmd").read_bytes() == b"one\r\ntwo\r\n"
    assert (tmp_path / "files/b.exe").read_bytes() == b"\n"


def test_list_files_drop_comments_blanks_and_whitespace(tmp_path: Path) -> None:
    path = tmp_path / "excluded.txt"
    path.write_bytes(b"# why\r\n\r\n  Test.One \r\n#Test.Two\nTest.Three\n")

    assert read_list(path) == ["Test.One", "Test.Three"]


def test_comment_only_list_file_is_empty(tmp_path: Path) -> None:
    path = tmp_path / "excluded.txt"
    path.write_text("# nothing excluded\n")

    assert not read_list(path)
