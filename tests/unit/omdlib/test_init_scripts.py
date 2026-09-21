#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from pathlib import Path

import pytest

from omdlib.init_scripts import all_stopped, check_status, daemon_states


def _create_init_script(site_dir: Path, name: str, exit_code: int) -> None:
    rc_dir = site_dir / "etc" / "rc.d"
    rc_dir.mkdir(parents=True, exist_ok=True)
    script = rc_dir / name
    script.write_text(f"#!/bin/sh\nexit {exit_code}\n")
    script.chmod(0o755)


def test_daemon_states(tmp_path: Path) -> None:
    _create_init_script(tmp_path, "10-nagios", 0)
    _create_init_script(tmp_path, "20-redis", 1)
    _create_init_script(tmp_path, "30-crontab", 5)

    assert daemon_states(str(tmp_path)) == [("nagios", 0), ("redis", 1), ("crontab", 5)]


def test_daemon_states_without_init_scripts(tmp_path: Path) -> None:
    assert daemon_states(str(tmp_path)) == []


@pytest.mark.parametrize(
    "states, expected",
    [
        pytest.param([1, 1, 5], 1, id="stopped"),
        pytest.param([0, 0, 5], 0, id="running"),
        pytest.param([0, 1, 5], 2, id="partially running"),
    ],
)
def test_check_status(tmp_path: Path, states: list[int], expected: int) -> None:
    for number, state in enumerate(states):
        _create_init_script(tmp_path, f"{number}0-daemon{number}", state)

    assert check_status(str(tmp_path), verbose=False, display=False) == expected


@pytest.mark.parametrize(
    "states, expected",
    [
        pytest.param([1, 1, 5], True, id="all daemons stopped"),
        pytest.param([0, 1, 5], False, id="one daemon running"),
        pytest.param([5, 5], False, id="all daemons unused"),
        pytest.param([], False, id="no init scripts"),
    ],
)
def test_all_stopped(states: list[int], expected: bool) -> None:
    assert all_stopped(states) is expected
