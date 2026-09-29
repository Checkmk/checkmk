#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Mapping, Sequence
from pathlib import Path

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


def test_precompile_filters_by_the_legacy_code_of_an_edition(tmp_path: Path) -> None:
    repo_root = _repository(
        tmp_path, {"1.md": werk_text(edition="community"), "2.md": werk_text(edition="pro")}
    )

    assert _precompiled_ids(tmp_path, repo_root, "--filter-by-edition", "cee") == [2]
