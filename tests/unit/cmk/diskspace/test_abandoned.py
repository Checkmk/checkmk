#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import os
from pathlib import Path

from cmk.diskspace.abandoned import _cleanup_host_directories


def test_cleanup_host_directories_recent_enough(tmp_path: Path) -> None:
    (recent_enough := tmp_path / "recent_enough").mkdir()
    (recent_enough_file1 := recent_enough / "file1").touch()
    os.utime(recent_enough, (12300003.0, 12300003.0))

    assert set() == _cleanup_host_directories(12300005.0, 3, set(), str(tmp_path))
    assert recent_enough_file1.exists()


def test_cleanup_host_directories_one_old_one_recent(tmp_path: Path) -> None:
    (recent_enough := tmp_path / "recent_enough").mkdir()
    (recent_enough_file1 := recent_enough / "file1").touch()
    os.utime(recent_enough, (12300003.0, 12300003.0))
    (ignored_outdated_file := recent_enough / "outdated").touch()
    os.utime(ignored_outdated_file, (12300000.0, 12300000.0))

    assert set() == _cleanup_host_directories(12300005.0, 3, set(), str(tmp_path))
    assert recent_enough_file1.exists()
    assert ignored_outdated_file.exists()


def test_cleanup_host_directories_outdated(tmp_path: Path) -> None:
    (outdated := tmp_path / "outdated_dir").mkdir()
    (outdated_file := outdated / "outdated").touch()
    os.utime(outdated_file, (12300000.0, 12300000.0))

    assert {"outdated_dir"} == _cleanup_host_directories(12300005.0, 3, set(), str(tmp_path))
    assert not outdated.exists()
