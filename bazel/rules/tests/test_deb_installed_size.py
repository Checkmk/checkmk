#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import io
import tarfile
from collections.abc import Sequence
from pathlib import Path

import pytest
from deb_installed_size import installed_size_kib, main


def _make_tar(path: Path, members: Sequence[tarfile.TarInfo]) -> Path:
    with tarfile.open(path, "w") as tar:
        for member in members:
            tar.addfile(member, io.BytesIO(b"\0" * member.size) if member.isreg() else None)
    return path


def _file(name: str, size: int) -> tarfile.TarInfo:
    member = tarfile.TarInfo(name)
    member.size = size
    return member


def _special(name: str, type_: bytes, linkname: str = "") -> tarfile.TarInfo:
    member = tarfile.TarInfo(name)
    member.type = type_
    member.linkname = linkname
    return member


@pytest.mark.parametrize(
    "size, expected_kib",
    [(0, 0), (1, 1), (1024, 1), (1025, 2), (10 * 1024 * 1024, 10 * 1024)],
)
def test_regular_file_rounds_up_to_kib(tmp_path: Path, size: int, expected_kib: int) -> None:
    archive = _make_tar(tmp_path / "data.tar", [_file("./f", size)])
    assert installed_size_kib(archive) == expected_kib


def test_directories_and_symlinks_count_one_kib(tmp_path: Path) -> None:
    archive = _make_tar(
        tmp_path / "data.tar",
        [_special("./dir", tarfile.DIRTYPE), _special("./link", tarfile.SYMTYPE, "target")],
    )
    assert installed_size_kib(archive) == 2


def test_hardlink_is_counted_once(tmp_path: Path) -> None:
    archive = _make_tar(
        tmp_path / "data.tar",
        [_file("./f", 4096), _special("./hard", tarfile.LNKTYPE, "./f")],
    )
    assert installed_size_kib(archive) == 4


def test_empty_archive(tmp_path: Path) -> None:
    assert installed_size_kib(_make_tar(tmp_path / "data.tar", [])) == 0


def test_main_writes_size_to_file(tmp_path: Path) -> None:
    archive = _make_tar(tmp_path / "data.tar", [_file("./f", 2048)])
    out = tmp_path / "installed_size"
    assert main(["--archive", str(archive), "--out", str(out)]) == 0
    assert out.read_text() == "2\n"
