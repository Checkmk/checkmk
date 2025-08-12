#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from pathlib import Path

from cmk.update_config.plugins.actions.persisted_sections import move_persisted_sections


def test_happy_path(tmp_path: Path) -> None:
    (tmp_path / "persisted").mkdir(parents=True, exist_ok=True)
    (tmp_path / "persisted/myhost").touch()

    move_persisted_sections(tmp_path)

    assert (tmp_path / "persisted_sections/agent/myhost").exists()


def test_destination_exists(tmp_path: Path) -> None:
    (tmp_path / "persisted").mkdir(parents=True, exist_ok=True)
    (tmp_path / "persisted/myhost").touch()
    (tmp_path / "persisted_sections/agent").mkdir(parents=True, exist_ok=True)

    move_persisted_sections(tmp_path)
    assert not (tmp_path / "persisted_sections/agent/agent").exists()


def test_source_does_not_exist(tmp_path: Path) -> None:
    move_persisted_sections(tmp_path)
    assert not (tmp_path / "persisted_sections/agent").exists()
