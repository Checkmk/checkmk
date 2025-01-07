#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import json
from dataclasses import dataclass
from pathlib import Path

import pytest

from cmk.gui.theme.choices import theme_choices


@dataclass(frozen=True, kw_only=True)
class _ThemeDirs:
    base_dir: Path
    local_base_dir: Path
    theme_dir: Path
    local_theme_dir: Path


@pytest.fixture(name="theme_dirs")
def fixture_theme_dirs(tmp_path: Path) -> _ThemeDirs:
    theme_path = tmp_path / "htdocs" / "themes"
    theme_path.mkdir(parents=True)
    local_theme_path = tmp_path / "local" / "htdocs" / "themes"
    local_theme_path.mkdir(parents=True)
    return _ThemeDirs(
        base_dir=tmp_path,
        local_base_dir=tmp_path / "local",
        theme_dir=theme_path,
        local_theme_dir=local_theme_path,
    )


@pytest.fixture(name="my_theme")
def fixture_my_theme(theme_dirs: _ThemeDirs) -> Path:
    my_dir = theme_dirs.theme_dir / "my_theme"
    my_dir.mkdir()
    (my_dir / "theme.json").open(mode="w", encoding="utf-8").write(
        str(json.dumps({"title": "Määh Theme :-)"}))
    )
    return my_dir


@pytest.mark.usefixtures("theme_dirs")
def test_theme_choices_empty() -> None:
    assert not theme_choices()


@pytest.mark.usefixtures("my_theme")
def test_theme_choices_normal(theme_dirs: _ThemeDirs) -> None:
    assert theme_choices(base_dirs=[theme_dirs.base_dir, theme_dirs.local_base_dir]) == [
        ("my_theme", "Määh Theme :-)")
    ]


@pytest.mark.usefixtures("my_theme")
def test_theme_choices_local_theme(theme_dirs: _ThemeDirs) -> None:
    my_dir = theme_dirs.local_theme_dir / "my_improved_theme"
    my_dir.mkdir()
    (my_dir / "theme.json").open(mode="w", encoding="utf-8").write(
        str(json.dumps({"title": "Määh Bettr Theme :-D"}))
    )

    assert theme_choices(base_dirs=[theme_dirs.base_dir, theme_dirs.local_base_dir]) == sorted(
        [
            ("my_theme", "Määh Theme :-)"),
            ("my_improved_theme", "Määh Bettr Theme :-D"),
        ]
    )


@pytest.mark.usefixtures("my_theme")
def test_theme_choices_override(theme_dirs: _ThemeDirs) -> None:
    my_dir = theme_dirs.local_theme_dir / "my_theme"
    my_dir.mkdir()
    (my_dir / "theme.json").open(mode="w", encoding="utf-8").write(
        str(json.dumps({"title": "Fixed theme"}))
    )

    assert theme_choices(base_dirs=[theme_dirs.base_dir, theme_dirs.local_base_dir]) == sorted(
        [
            ("my_theme", "Fixed theme"),
        ]
    )


def test_theme_broken_meta(
    theme_dirs: _ThemeDirs,
    my_theme: Path,
) -> None:
    (my_theme / "theme.json").open(mode="w", encoding="utf-8").write('{"titlewrong": xyz"bla"}')

    assert theme_choices(base_dirs=[theme_dirs.base_dir, theme_dirs.local_base_dir]) == sorted(
        [
            ("my_theme", "my_theme"),
        ]
    )
