#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import argparse
from pathlib import Path

import pytest

from cmk.utils.werks.announce import main


def _werk(version: str | None) -> str:
    version_row = "" if version is None else f"version    | {version}\n"
    return (
        "[//]: # (werk v3)\n"
        "# Some title\n"
        "\n"
        "key        | value\n"
        "---------- | ---\n"
        "date       | 2026-07-23T08:04:44.815279+00:00\n"
        f"{version_row}"
        "class      | fix\n"
        "edition    | community\n"
        "component  | core\n"
        "level      | 1\n"
        "compatible | yes\n"
        "\n"
        "Some description.\n"
    )


def test_announce_includes_unburned_werks(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    (tmp_path / "defines.make").write_text("VERSION            := 2.5.0p16\n")
    werk_dir = tmp_path / ".werks"
    werk_dir.mkdir()
    (werk_dir / "1001.md").write_text(_werk("2.5.0p16"))
    (werk_dir / "1002.md").write_text(_werk(None))
    (werk_dir / "1003.md").write_text(_werk("2.5.0p15"))

    main(argparse.Namespace(werk_dir=werk_dir, version="2.5.0p16", format="md"))

    announcement = capsys.readouterr().out
    assert "werk/1001" in announcement
    assert "werk/1002" in announcement
    assert "werk/1003" not in announcement


def test_announce_other_version_excludes_unburned_werks(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    (tmp_path / "defines.make").write_text("VERSION            := 2.5.0p17\n")
    werk_dir = tmp_path / ".werks"
    werk_dir.mkdir()
    (werk_dir / "1002.md").write_text(_werk(None))
    (werk_dir / "1003.md").write_text(_werk("2.5.0p16"))
    (werk_dir / "1004.md").write_text(_werk("2.5.0p17"))

    main(argparse.Namespace(werk_dir=werk_dir, version="2.5.0p16", format="md"))

    announcement = capsys.readouterr().out
    assert "werk/1002" not in announcement
    assert "werk/1003" in announcement
    assert "werk/1004" not in announcement
