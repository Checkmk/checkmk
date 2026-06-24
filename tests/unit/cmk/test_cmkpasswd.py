#!/usr/bin/env python3
# Copyright (C) 2022 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
from io import StringIO
from pathlib import Path
from unittest.mock import patch

import pytest
from pytest import MonkeyPatch

from cmk.cmkpasswd.main import main

Capsys = pytest.CaptureFixture[str]


@pytest.fixture(name="htpasswd_path")
def fixture_htpasswd_path(monkeypatch: MonkeyPatch, tmp_path: Path) -> Path:
    file_ = tmp_path / "htpasswd"
    monkeypatch.setattr("cmk.cmkpasswd.main.HTPASSWD_FILE", file_)
    return file_


@pytest.mark.parametrize(
    "password",
    [
        pytest.param("hunter2", id="ascii"),
        pytest.param("🙈 🙉 🙊", id="unicode"),
    ],
)
def test_main_prints_hashed_entry(capsys: Capsys, password: str) -> None:
    with patch("sys.stdin", StringIO(password)):
        assert main(args=["--dry-run", "--stdin", "testuser"]) == 0
        captured = capsys.readouterr()
        assert captured.err == ""
        assert captured.out.startswith("testuser:$")


@pytest.mark.parametrize("old_content", ["", "cmkadmin:nimdakmc\nauto:mation"])
def test_main_writes_file(htpasswd_path: Path, old_content: str) -> None:
    htpasswd_path.write_text(old_content, encoding="utf-8")
    with patch("sys.stdin", StringIO("hunter2")):
        assert main(args=["--stdin", "testuser"]) == 0
    new = htpasswd_path.read_text(encoding="utf-8").splitlines()
    old = old_content.splitlines()
    assert len(new) == len(old) + 1
    assert any(l.startswith("testuser:$") for l in new)
    assert all(l in new for l in old)


@pytest.mark.parametrize(
    "password",
    [
        # This test might break if we switch from bcrypt and start allowing
        # null bytes in passwords. More likely we'll continue to forbid these though.
        pytest.param("\0", id="null byte in password"),
        # This test will break if we switch from bcrypt.
        pytest.param(73 * "|", id="password too long for bcrypt"),
    ],
)
def test_main_with_invalid_passwords_is_an_error(capsys: Capsys, password: str) -> None:
    with patch("sys.stdin", StringIO(password)):
        assert main(args=["-i", "longcat"]) != 0
        assert "password" in capsys.readouterr().err.lower()


def test_main_invalid_user(capsys: Capsys) -> None:
    # Make sure that, when given an invalid username, no password is prompted for.
    # If this logic is broken the test might hang rather than fail.
    assert main(args=["what?user?"]) != 0
    captured = capsys.readouterr()
    assert "username" in captured.err.lower()


def test_main_does_not_write_stdout_on_error(capsys: Capsys) -> None:
    with patch("sys.stdin", StringIO("|" * 100)):
        assert main(args=["--stdin", "testuser"]) != 0
        captured = capsys.readouterr()
        assert captured.out == ""


def test_file_not_found(capsys: Capsys, htpasswd_path: Path) -> None:
    with patch("sys.stdin", StringIO("hunter2")):
        assert main(args=["testuser", "--stdin"]) != 0

        captured = capsys.readouterr()
        assert captured.out == ""
        assert "No such file" in captured.err and htpasswd_path.name in captured.err
