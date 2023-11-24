#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from pathlib import Path

from cmk.mkp_tool import PackagePart, PathConfig
from cmk.mkp_tool._reporter import _all_local_files, all_packable_files


def _setup_local_files_structure(path_config: PathConfig) -> None:
    for part in PackagePart:
        part_path = path_config.get_path(part)
        subdir = part_path / "subdir"
        subdir.mkdir(parents=True)
        (part_path / f"regular_file_of_{part.ident}.py").touch()
        (part_path / f".hidden_file_of_{part.ident}.py").touch()
        (part_path / f"editor_file_of_{part.ident}.py~").touch()
        (part_path / f"compiled_file_of_{part.ident}.pyc").touch()
        (subdir / f"subdir_file_of_{part.ident}.py").touch()

    other_file = path_config.local_root / "some" / "other" / "file.sh"
    other_file.parent.mkdir(parents=True)
    other_file.touch()


def test_get_local_files_by_part(path_config: PathConfig) -> None:
    _setup_local_files_structure(path_config)
    expected: dict[PackagePart | None, set[Path]] = {
        **{
            p: {Path(f"regular_file_of_{p.ident}.py"), Path(f"subdir/subdir_file_of_{p.ident}.py")}
            for p in PackagePart
            if p is not PackagePart.EC_RULE_PACKS
        },
        None: {
            path_config.local_root / "some" / "other" / "file.sh",
        },
    }
    assert _all_local_files(path_config) == expected


def test_get_packable_files_by_part(path_config: PathConfig) -> None:
    _setup_local_files_structure(path_config)

    expected: dict[PackagePart, set[Path]] = {
        **{
            p: {Path(f"regular_file_of_{p.ident}.py"), Path(f"subdir/subdir_file_of_{p.ident}.py")}
            for p in PackagePart
            if p is not PackagePart.EC_RULE_PACKS
        },
        PackagePart.EC_RULE_PACKS: {
            Path(".hidden_file_of_ec_rule_packs.py"),
            Path("compiled_file_of_ec_rule_packs.pyc"),
            Path("editor_file_of_ec_rule_packs.py~"),
            Path("regular_file_of_ec_rule_packs.py"),
            Path("subdir"),
        },
    }
    assert all_packable_files(path_config) == expected
