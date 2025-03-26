#!/usr/bin/env python3
# Copyright (C) 2022 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Callable
from io import StringIO
from pathlib import Path
from unittest.mock import patch

import pytest
from pytest import MonkeyPatch

from cmk.cmkpasswd import _run_cmkpasswd, InvalidPasswordError, InvalidUsernameError, main
from cmk.crypto.password import Password

Capsys = pytest.CaptureFixture[str]


def _get_pw(pw: str = "hunter2") -> Callable[[], Password]:
    return lambda: Password(pw)


@pytest.mark.parametrize(
    "user,password",
    [
        ("testuser", "hunter2"),
        ("unicode", "🙈 🙉 🙊"),
    ],
)
def test_print(capsys: Capsys, user: str, password: str) -> None:
    _run_cmkpasswd(user, _get_pw(password), None)
    captured = capsys.readouterr()
    assert captured.err == ""
    assert captured.out.startswith(f"{user}:$")


@pytest.mark.parametrize("old_content", ["", "cmkadmin:nimdakmc\nauto:mation"])
def test_write_file(tmp_path: Path, old_content: str) -> None:
    f = tmp_path / "htpasswd"
    f.touch()
    f.write_text(old_content, encoding="utf-8")

    _run_cmkpasswd("testuser", _get_pw(), f)

    new = f.read_text(encoding="utf-8").splitlines()
    old = old_content.splitlines()
    assert len(new) == len(old) + 1
    assert any(l.startswith("testuser:$") for l in new)
    assert all(l in new for l in old)


def test_filenotfound(tmp_path: Path) -> None:
    with pytest.raises(OSError):
        _run_cmkpasswd("testuser", _get_pw(), tmp_path / "not" / "here")


def test_verification_error() -> None:
    def raise_err() -> Password:
        raise ValueError("test error")

    # This basically only tests that the error is propagated from the get_password function
    with pytest.raises(ValueError, match="test error"):
        _run_cmkpasswd("testuser", raise_err, None)


def test_invalid_user() -> None:
    with pytest.raises(InvalidUsernameError, match="invalid username"):
        _run_cmkpasswd("test🔥user", _get_pw(), None)


def test_invalid_password() -> None:
    with pytest.raises(InvalidPasswordError, match="Password too long"):
        # This test will break if we switch from bcrypt.
        _run_cmkpasswd("testuser", _get_pw(73 * "a"), None)

    with pytest.raises(InvalidPasswordError):
        # This test might break if we switch from bcrypt and start allowing
        # null bytes in passwords. More likely we'll continue to forbid these though.
        _run_cmkpasswd("testuser", _get_pw("null\0byte"), None)


@pytest.fixture(name="htpasswd_path")
def fixture_htpasswd_path(monkeypatch: MonkeyPatch, tmp_path: Path) -> Path:
    file_ = tmp_path / "htpasswd"
    monkeypatch.setattr("cmk.cmkpasswd.HTPASSWD_FILE", file_)
    return file_


def test_main_success(htpasswd_path: Path) -> None:
    htpasswd_path.touch()
    with patch("sys.stdin", StringIO("hunter2")):
        assert main(args=["-i", "testuser"]) == 0


@pytest.mark.parametrize(
    "user,password,reason",
    [
        ("", "\0", "password"),  # Null byte not allowed
        ("longcat", 73 * "|", "password"),  # Too long for bcrypt
        ("what?user?", "hunter2", "username"),  # Invalid username
    ],
)
def test_main_errors(capsys: Capsys, user: str, password: str, reason: str) -> None:
    with patch("sys.stdin", StringIO(password)):
        assert main(args=["-i", user]) != 0

        captured = capsys.readouterr()
        assert captured.out == ""
        assert reason in captured.err.lower()


def test_file_not_found(capsys: Capsys, htpasswd_path: Path) -> None:
    with patch("sys.stdin", StringIO("hunter2")):
        assert main(args=["testuser", "-i"]) != 0

        captured = capsys.readouterr()
        assert captured.out == ""
        assert "No such file" in captured.err and htpasswd_path.name in captured.err


def test_main_invalid_username() -> None:
    # Make sure that, when given an invalid username, no password is prompted for.
    # If this logic is broken the test might hang rather than fail.
    assert main(args=["invalid user?!"]) != 0
