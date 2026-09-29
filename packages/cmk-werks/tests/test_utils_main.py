#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Mapping, Sequence
from pathlib import Path

import pytest

from cmk.werks.tool import parse_werk
from cmk.werks.tool.utils import load_precompiled_werks_file
from cmk.werks.tool.utils.__main__ import main

from ._werk_files import werk_text


def _repository(tmp_path: Path, werk_files: Mapping[str, str], version: str = "2.5.0") -> Path:
    repo_root = tmp_path / "repo"
    werk_dir = repo_root / ".werks"
    werk_dir.mkdir(parents=True)
    (repo_root / "defines.make").write_text(f"VERSION := {version}\n", encoding="utf-8")
    for name, content in werk_files.items():
        (werk_dir / name).write_text(content, encoding="utf-8")
    return repo_root


def _precompiled_ids(tmp_path: Path, repo_root: Path, *options: str) -> Sequence[int]:
    destination = tmp_path / "precompiled.json"
    main(["precompile", str(repo_root / ".werks"), str(destination), *options])
    return sorted(load_precompiled_werks_file(destination))


def test_precompile_keeps_the_werks_of_the_current_release(tmp_path: Path) -> None:
    repo_root = _repository(
        tmp_path,
        {"1.md": werk_text(version="2.5.0"), "2.md": werk_text(version="2.4.0p3")},
        version="2.5.0b1",
    )

    assert _precompiled_ids(tmp_path, repo_root) == [1]


def test_precompile_keeps_the_werks_of_the_given_edition(tmp_path: Path) -> None:
    repo_root = _repository(
        tmp_path, {"1.md": werk_text(edition="community"), "2.md": werk_text(edition="pro")}
    )

    assert _precompiled_ids(tmp_path, repo_root, "--filter-by-edition", "pro") == [2]


def test_precompile_filters_by_the_legacy_code_of_an_edition(tmp_path: Path) -> None:
    repo_root = _repository(
        tmp_path, {"1.md": werk_text(edition="community"), "2.md": werk_text(edition="pro")}
    )

    assert _precompiled_ids(tmp_path, repo_root, "--filter-by-edition", "cee") == [2]


def test_precompile_fails_for_a_werk_it_cannot_load(tmp_path: Path) -> None:
    repo_root = _repository(tmp_path, {"1.md": "no werk"})

    with pytest.raises(RuntimeError, match="Could not parse werk"):
        _precompiled_ids(tmp_path, repo_root)


def test_burn_writes_the_release_version_into_a_werk_without_one(tmp_path: Path) -> None:
    unreleased = werk_text(version=None)
    repo_root = _repository(tmp_path, {"1.md": unreleased}, version="2.5.0p2")

    main(["burn", str(repo_root)])

    burned = (repo_root / ".werks/1.md").read_text(encoding="utf-8")
    assert parse_werk(burned, "1.md").metadata["version"] == "2.5.0p2"


def test_burn_reports_how_many_werks_it_burned(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    unreleased = werk_text(version=None)
    repo_root = _repository(
        tmp_path, {"1.md": unreleased, "2.md": werk_text(), "first_free": "3\n"}
    )

    main(["burn", str(repo_root)])

    assert capsys.readouterr().out == "Burned 1 Werks.\n"


def test_burn_fails_for_a_werk_it_cannot_parse(tmp_path: Path) -> None:
    repo_root = _repository(tmp_path, {"1.md": "no werk"})

    with pytest.raises(RuntimeError, match="can not be parsed as werk"):
        main(["burn", str(repo_root)])
