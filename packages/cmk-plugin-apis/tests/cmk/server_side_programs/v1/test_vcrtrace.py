#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Iterator
from contextlib import chdir
from pathlib import Path
from unittest.mock import patch

import pytest

from cmk.server_side_programs.v1_unstable._vcrtrace import _check_path

ALLOWDIR = "tmp/check_mk/debug"


@pytest.fixture(name="mocked_home")
def _mocked_home(tmp_path: Path) -> Iterator[Path]:
    with patch("os.environ", {"HOME": str(tmp_path)}):
        yield tmp_path


def test_check_path_relative_ok(mocked_home: Path) -> None:
    (mocked_home / ALLOWDIR).mkdir(parents=True, exist_ok=True)
    with chdir(mocked_home):
        _check_path(f"{ALLOWDIR}/foo")


def test_check_path_relative_missing(mocked_home: Path) -> None:
    with chdir(mocked_home), pytest.raises(NotADirectoryError):
        _check_path(f"{ALLOWDIR}/foo")


def test_check_path_relative_too_far_down(mocked_home: Path) -> None:
    (mocked_home / ALLOWDIR).mkdir(parents=True, exist_ok=True)
    with chdir(mocked_home / "tmp"), pytest.raises(ValueError):
        _check_path(f"{ALLOWDIR}/foo")


def test_check_path_relative_too_far_up(mocked_home: Path) -> None:
    (mocked_home / ALLOWDIR).mkdir(parents=True, exist_ok=True)
    with chdir(mocked_home / ".."), pytest.raises(ValueError):
        _check_path(f"{ALLOWDIR}/foo")


def test_check_path_absolute_ok(mocked_home: Path) -> None:
    (mocked_home / ALLOWDIR).mkdir(parents=True, exist_ok=True)
    _check_path(str(mocked_home / f"{ALLOWDIR}/foo"))


def test_check_path_absolute_missing(mocked_home: Path) -> None:
    with pytest.raises(NotADirectoryError):
        _check_path(str(mocked_home / f"{ALLOWDIR}/foo"))


def test_check_path_absolute_invalid(mocked_home: Path) -> None:
    (mocked_home / ALLOWDIR).mkdir(parents=True, exist_ok=True)
    with chdir(mocked_home / "tmp"), pytest.raises(ValueError):
        _check_path(str(mocked_home / "something/else/foo"))
