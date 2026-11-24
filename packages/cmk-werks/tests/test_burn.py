#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from pathlib import Path

from cmk.werks import parse_werk
from cmk.werks.utils.burn import main as burn


def _werk(version: str | None) -> str:
    version_row = "" if version is None else f"version    | {version}\n"
    return (
        "[//]: # (werk v2)\n"
        "# Some title\n"
        "\n"
        "key        | value\n"
        "---------- | ---\n"
        "date       | 2026-07-23T08:04:44.815279+00:00\n"
        f"{version_row}"
        "class      | fix\n"
        "edition    | cre\n"
        "component  | core\n"
        "level      | 1\n"
        "compatible | yes\n"
        "\n"
        "Some description.\n"
    )


def _repo(tmp_path: Path) -> Path:
    (tmp_path / "defines.make").write_text("VERSION            := 2.4.0p16\n")
    werk_dir = tmp_path / ".werks"
    werk_dir.mkdir()
    (werk_dir / "config").write_text("")
    (werk_dir / "first_free").write_text("1234\n")
    return tmp_path


def test_burn_writes_the_version_into_a_werk_without_version(tmp_path: Path) -> None:
    repo = _repo(tmp_path)
    werk_file = repo / ".werks/1001.md"
    werk_file.write_text(_werk(None))

    burn(repo)

    assert parse_werk(werk_file.read_text(), werk_file.name).metadata["version"] == "2.4.0p16"


def test_burn_keeps_a_werk_with_version(tmp_path: Path) -> None:
    repo = _repo(tmp_path)
    werk_file = repo / ".werks/1001.md"
    werk_file.write_text(_werk("2.4.0p15"))

    burn(repo)

    assert werk_file.read_text() == _werk("2.4.0p15")
