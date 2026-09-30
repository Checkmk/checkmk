#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import re
from collections.abc import Sequence
from pathlib import Path

import pytest

from cmk.werks.tool.validate import main, run

from ._werk_files import werk_text

_VERSION_REGEX = re.compile(r"^\d.\d.\d([ipb]\d+)?$")

_CONFIG = """
editions = [("community", "Community")]
components = [("core", "Core")]
edition_components = {}
classes = [("fix", "Bug fix", "FIX")]
levels = [("1", "Trivial change")]
compatible = [("yes", "Compatible"), ("no", "Incompatible")]
online_url = "https://checkmk.com/werk/%d"
"""


def _validate(tmp_path: Path, werk_files: list[Path]) -> None:
    config = tmp_path / "config"
    config.write_text(_CONFIG, encoding="utf-8")
    defines_make = tmp_path / "defines.make"
    defines_make.write_text("VERSION := 2.5.0\n", encoding="utf-8")
    main(werk_files, config, defines_make, _VERSION_REGEX)


def _write_werk(tmp_path: Path, text: str) -> Path:
    werk = tmp_path / "1234.md"
    werk.write_text(text, encoding="utf-8")
    return werk


def test_valid_werks_are_reported_as_validated(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    werk = _write_werk(tmp_path, werk_text())

    _validate(tmp_path, [werk])

    assert capsys.readouterr().out == "Successfully validated 1 werks\n"


@pytest.mark.parametrize(
    "text, reason",
    [
        pytest.param(werk_text(component="unknown"), "Component 'unknown'", id="unknown-component"),
        pytest.param(werk_text(version="2.5"), "Version '2.5' is not valid", id="invalid-version"),
    ],
)
def test_an_invalid_werk_is_rejected(tmp_path: Path, text: str, reason: str) -> None:
    werk = _write_werk(tmp_path, text)

    with pytest.raises(RuntimeError) as excinfo:
        _validate(tmp_path, [werk])

    assert reason in str(excinfo.value.__cause__)


def test_a_file_that_is_no_werk_is_skipped(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    readme = tmp_path / "README.md"
    readme.write_text("not a werk", encoding="utf-8")

    _validate(tmp_path, [readme])

    assert f"WARNING: NOT CHECKING {readme} as it's not a werk." in capsys.readouterr().out


def _repository(tmp_path: Path, werk_names: Sequence[str]) -> Path:
    werks_dir = tmp_path / ".werks"
    werks_dir.mkdir()
    (werks_dir / "config").write_text(_CONFIG, encoding="utf-8")
    (tmp_path / "defines.make").write_text("VERSION := 2.5.0\n", encoding="utf-8")
    for name in werk_names:
        (werks_dir / name).write_text(werk_text(), encoding="utf-8")
    return tmp_path


def test_run_validates_the_given_werks(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    repo = _repository(tmp_path, ["1.md", "2.md"])

    run([".werks/1.md"], {}, repo)

    assert capsys.readouterr().out == "Successfully validated 1 werks\n"


def test_run_validates_the_werks_changed_in_ci(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    repo = _repository(tmp_path, ["1.md", "2.md", "3.md"])

    run([], {"CHANGED_WERK_FILES": ".werks/1.md .werks/2.md"}, repo)

    assert capsys.readouterr().out == "Successfully validated 2 werks\n"


def test_run_validates_every_werk_without_a_choice(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    repo = _repository(tmp_path, ["1.md", "2.md", "3.md"])

    run([], {}, repo)

    assert capsys.readouterr().out == "Successfully validated 3 werks\n"


def test_run_checks_the_version_against_the_given_pattern(tmp_path: Path) -> None:
    repo = _repository(tmp_path, ["1.md"])

    with pytest.raises(RuntimeError) as excinfo:
        run(["--version-regex", "^3", ".werks/1.md"], {}, repo)

    assert "Version '2.5.0' is not valid" in str(excinfo.value.__cause__)
