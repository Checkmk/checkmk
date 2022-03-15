#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import pathlib
import tarfile
from typing import Generator

from cmk.gui.watolib import snapshots


def _snapshot_files() -> Generator[pathlib.Path, None, None]:
    yield from pathlib.Path(snapshots.snapshot_dir).glob("wato-snapshot*.tar")


def test_create_snapshot() -> None:
    snapshots.create_snapshot(None)
    assert list(_snapshot_files())


def test_snapshot_status() -> None:
    snapshots.create_snapshot("test snapshot")
    snapshot_status = snapshots.get_snapshot_status(next(_snapshot_files()).name)
    # bug, will be fixed in the next commit
    assert not snapshot_status["comment"]
    assert snapshot_status["broken"]
    assert snapshot_status["broken_text"]


def test_extract_snapshot() -> None:
    snapshots.create_snapshot(None)
    with tarfile.open(next(_snapshot_files()), mode="r") as snapshot_tar:
        snapshots.extract_snapshot(
            snapshot_tar,
            snapshots.backup_domains,
        )
