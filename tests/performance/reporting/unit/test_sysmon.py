#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from pathlib import Path

import pytest

from tests.performance.sysmon import auto_increment_filename, track_resources


def test_a_repeated_name_gets_the_next_number(tmp_path: Path) -> None:
    names = []
    for _ in range(3):
        path = auto_increment_filename(tmp_path / "test_x[a].resources.json", ".resources.json")
        path.touch()
        names.append(path.name)
    assert names == [
        "test_x[a].resources.json",
        "test_x[a].1.resources.json",
        "test_x[a].2.resources.json",
    ]


def test_a_dot_in_a_name_becomes_a_hyphen(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("TEST_UNDECLARED_OUTPUTS_DIR", str(tmp_path))
    with track_resources("test_x[1.5]", sampling_interval=0.2):
        pass
    assert [path.name for path in tmp_path.iterdir()] == ["test_x[1-5].resources.json"]
