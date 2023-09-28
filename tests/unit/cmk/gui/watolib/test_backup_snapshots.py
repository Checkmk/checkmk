#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import pathlib
import tarfile
from collections.abc import Generator

from cmk.gui.watolib import backup_snapshots


def _snapshot_files() -> Generator[pathlib.Path, None, None]:
    yield from pathlib.Path(backup_snapshots.snapshot_dir).glob("wato-snapshot*.tar")


def test_create_snapshot() -> None:
    backup_snapshots.create_snapshot("")
    assert list(_snapshot_files())


def test_snapshot_status() -> None:
    backup_snapshots.create_snapshot("test snapshot")
    snapshot_status = backup_snapshots.get_snapshot_status(next(_snapshot_files()).name)
    assert "test snapshot" in snapshot_status["comment"]
    assert not snapshot_status["broken"]
    assert "broken_text" not in snapshot_status


def test_extract_snapshot() -> None:
    backup_snapshots.create_snapshot("")
    with tarfile.open(next(_snapshot_files()), mode="r") as snapshot_tar:
        backup_snapshots.extract_snapshot(
            snapshot_tar,
            backup_snapshots.backup_domains,
        )
