#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import argparse
import ast
from pathlib import Path

import pytest

from cmk.ccc.profile import Profile

from cmk.plugins.kube.special_agents.agent_kube import _profile_file


@pytest.fixture(name="debug_dir")
def _debug_dir(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> Path:
    monkeypatch.setenv("HOME", str(tmp_path))
    debug_dir = tmp_path / "tmp" / "check_mk" / "debug"
    debug_dir.mkdir(parents=True)
    return debug_dir


def test_profile_file_inside_debug_dir(debug_dir: Path) -> None:
    assert _profile_file(str(debug_dir / "profile.out")) == debug_dir / "profile.out"


@pytest.mark.parametrize(
    "relative_path",
    [
        pytest.param("profile.out", id="home"),
        pytest.param("tmp/check_mk/debug/../profile.out", id="traversal"),
    ],
)
def test_profile_file_outside_debug_dir_rejected(debug_dir: Path, relative_path: str) -> None:
    home = debug_dir.parent.parent.parent
    with pytest.raises(argparse.ArgumentTypeError):
        _profile_file(str(home / relative_path))


def test_profile_script_does_not_execute_path(debug_dir: Path) -> None:
    profile_file = debug_dir / 'p") if 0 else None;import os;os.system("id")#'
    with Profile(enabled=True, profile_file=profile_file):
        pass
    tree = ast.parse(profile_file.with_suffix(".py").read_text())
    (stats_call,) = (
        node
        for node in ast.walk(tree)
        if isinstance(node, ast.Call)
        and isinstance(node.func, ast.Attribute)
        and node.func.attr == "Stats"
    )
    assert len(stats_call.args) == 1
    assert isinstance(stats_call.args[0], ast.Constant)
    assert stats_call.args[0].value == str(profile_file)
