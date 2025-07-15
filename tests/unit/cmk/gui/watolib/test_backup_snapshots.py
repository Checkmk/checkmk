#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import pathlib
import tarfile
from collections.abc import Generator

import pytest

from cmk.ccc.user import UserId

from cmk.gui.watolib import backup_snapshots


def _snapshot_files() -> Generator[pathlib.Path, None, None]:
    yield from pathlib.Path(backup_snapshots.snapshot_dir).glob("wato-snapshot*.tar")


@pytest.mark.usefixtures("patch_omd_site")
def test_create_snapshot() -> None:
    backup_snapshots.create_snapshot(
        comment="",
        created_by=None,
        secret=b"abc",
        max_snapshots=10,
        use_git=False,
        debug=False,
    )
    assert list(_snapshot_files())


@pytest.mark.usefixtures("patch_omd_site")
def test_snapshot_status() -> None:
    backup_snapshots.create_snapshot(
        comment="test snapshot",
        created_by=UserId(""),
        secret=b"abc",
        max_snapshots=10,
        use_git=False,
        debug=False,
    )
    snapshot_status = backup_snapshots.get_snapshot_status(
        snapshot=next(_snapshot_files()).name,
        debug=False,
    )
    assert "test snapshot" in snapshot_status["comment"]
    assert not snapshot_status["broken"]
    assert "broken_text" not in snapshot_status


@pytest.mark.usefixtures("patch_omd_site")
def test_extract_snapshot() -> None:
    backup_snapshots.create_snapshot(
        comment="",
        created_by=UserId("harry"),
        secret=b"abc",
        max_snapshots=10,
        use_git=False,
        debug=False,
    )
    with tarfile.open(next(_snapshot_files()), mode="r") as snapshot_tar:
        backup_snapshots.extract_snapshot(
            snapshot_tar,
            backup_snapshots.backup_domains,
        )
