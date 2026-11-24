#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import os
import pstats
import subprocess
import sys
from pathlib import Path

import pytest

from cmk.ccc.profile import Profile, profile_call


def _work() -> int:
    return sum(range(10))


def _profiled_functions(profile_file: Path) -> set[str]:
    return set(pstats.Stats(str(profile_file)).get_stats_profile().func_profiles)


def test_profile_writes_the_stats_of_the_block(tmp_path: Path) -> None:
    profile_file = tmp_path / "work.profile"

    with Profile(profile_file=profile_file):
        _work()

    assert "_work" in _profiled_functions(profile_file)


def test_profile_writes_a_script_printing_the_stats(tmp_path: Path) -> None:
    with Profile(profile_file=tmp_path / "work.profile"):
        _work()

    printed = subprocess.run(
        [sys.executable, "-I", str(tmp_path / "work.py")],
        capture_output=True,
        text=True,
        check=True,
    ).stdout

    assert "_work" in printed


def test_profile_writes_an_executable_script(tmp_path: Path) -> None:
    with Profile(profile_file=tmp_path / "work.profile"):
        _work()

    assert os.access(tmp_path / "work.py", os.X_OK)


def test_profile_without_a_file_prints_the_stats(capsys: pytest.CaptureFixture[str]) -> None:
    with Profile():
        _work()

    assert "_work" in capsys.readouterr().out


def test_disabled_profile_writes_nothing(tmp_path: Path) -> None:
    with Profile(enabled=False, profile_file=tmp_path / "work.profile"):
        _work()

    assert not list(tmp_path.iterdir())


def test_profiled_call_returns_the_result_of_the_function(tmp_path: Path) -> None:
    work = profile_call(base_dir=str(tmp_path))(_work)

    assert work() == 45


def test_profiled_call_writes_a_profile_named_after_the_function(tmp_path: Path) -> None:
    work = profile_call(base_dir=str(tmp_path))(_work)

    work()

    (profile_file,) = tmp_path.glob("_work_*.profile")
    assert "_work" in _profiled_functions(profile_file)
