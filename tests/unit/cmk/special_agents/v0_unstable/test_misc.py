#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Iterator
from contextlib import chdir
from pathlib import Path
from unittest.mock import patch

import pytest

from cmk.special_agents.v0_unstable.misc import _check_path


@pytest.fixture(name="mocked_home")
def _mocked_home(tmp_path: Path) -> Iterator[Path]:
    with patch("os.environ", {"HOME": str(tmp_path)}):
        yield tmp_path


def test_check_path_relative(mocked_home: Path) -> None:
    with chdir(mocked_home):
        with pytest.raises(ValueError):
            _check_path("foo")
        _check_path("tmp/debug/foo")

    some_dir = mocked_home / "foobar"
    some_dir.mkdir()
    with chdir(some_dir):
        with pytest.raises(ValueError):
            _check_path("tmp/debug/foo")
        _check_path("../tmp/debug/foo")


def test_check_path_absolute(mocked_home: Path) -> None:
    with pytest.raises(ValueError):
        _check_path(str(mocked_home / "foo"))
    _check_path(str(mocked_home / "tmp" / "debug" / "foo"))
