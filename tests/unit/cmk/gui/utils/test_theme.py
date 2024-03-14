#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import json
from collections.abc import Generator
from pathlib import Path

import pytest
from pytest import MonkeyPatch

import cmk.utils.paths

from cmk.gui.utils.theme import theme, theme_choices


@pytest.fixture(name="theme_dirs")
def fixture_theme_dirs(tmp_path: Path, monkeypatch: MonkeyPatch) -> tuple[Path, Path]:
    theme_path = tmp_path / "htdocs" / "themes"
    theme_path.mkdir(parents=True)

    local_theme_path = tmp_path / "local" / "htdocs" / "themes"
    local_theme_path.mkdir(parents=True)

    monkeypatch.setattr(cmk.utils.paths, "web_dir", str(tmp_path))
    monkeypatch.setattr(cmk.utils.paths, "local_web_dir", tmp_path / "local")

    return theme_path, local_theme_path


@pytest.fixture(name="my_theme")
def fixture_my_theme(
    theme_dirs: tuple[Path, Path], monkeypatch: MonkeyPatch
) -> Generator[Path, None, None]:
    theme_path = theme_dirs[0]
    my_dir = theme_path / "my_theme"
    my_dir.mkdir()
    (my_dir / "theme.json").open(mode="w", encoding="utf-8").write(
        str(json.dumps({"title": "Määh Theme :-)"}))
    )

    theme.theme_choices.append(("my_theme", "Määh Theme :-)"))
    # Update the theme choices after introducing a new theme here
    yield my_dir

    del theme.theme_choices[-1]


@pytest.mark.usefixtures("theme_dirs")
def test_theme_choices_empty() -> None:
    assert theme_choices() == []


@pytest.mark.usefixtures("request_context", "my_theme")
def test_theme_choices_normal() -> None:
    assert theme_choices() == [("my_theme", "Määh Theme :-)")]


@pytest.mark.usefixtures("request_context", "my_theme")
def test_theme_choices_local_theme(theme_dirs: tuple[Path, Path]) -> None:
    local_theme_path = theme_dirs[1]

    my_dir = local_theme_path / "my_improved_theme"
    my_dir.mkdir()
    (my_dir / "theme.json").open(mode="w", encoding="utf-8").write(
        str(json.dumps({"title": "Määh Bettr Theme :-D"}))
    )

    assert theme_choices() == sorted(
        [
            ("my_theme", "Määh Theme :-)"),
            ("my_improved_theme", "Määh Bettr Theme :-D"),
        ]
    )


@pytest.mark.usefixtures("request_context", "my_theme")
def test_theme_choices_override(theme_dirs: tuple[Path, Path]) -> None:
    local_theme_path = theme_dirs[1]

    my_dir = local_theme_path / "my_theme"
    my_dir.mkdir()
    (my_dir / "theme.json").open(mode="w", encoding="utf-8").write(
        str(json.dumps({"title": "Fixed theme"}))
    )

    assert theme_choices() == sorted(
        [
            ("my_theme", "Fixed theme"),
        ]
    )


def test_theme_broken_meta(request_context: None, my_theme: Path) -> None:
    (my_theme / "theme.json").open(mode="w", encoding="utf-8").write('{"titlewrong": xyz"bla"}')

    assert theme_choices() == sorted(
        [
            ("my_theme", "my_theme"),
        ]
    )
