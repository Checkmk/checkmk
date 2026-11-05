#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import json
from collections.abc import Iterator
from contextlib import chdir
from pathlib import Path
from unittest.mock import patch

import pytest

from cmk.special_agents.v0_unstable.misc import _check_path, JsonCachedData
from cmk.special_agents.v0_unstable.storage import Storage


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


@pytest.mark.xfail(strict=True, raises=json.JSONDecodeError, reason="Crash groups 4930, 4653")
def test_json_cached_data_starts_over_on_truncated_cache(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("OMD_ROOT", str(tmp_path))
    storage = Storage("proxmox_ve", "myhost")
    storage.write("backup_logs", '{\n  "task-1": [\n    {')

    with JsonCachedData(storage, "backup_logs", lambda _key, _data: False) as setdefault:
        assert setdefault("task-1", lambda: ["log line"]) == ["log line"]

    assert json.loads(storage.read("backup_logs", "")) == {"task-1": ["log line"]}
