#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import io
import os
import pathlib
import tarfile
from collections.abc import Generator

import pytest

import cmk.utils.paths
from cmk.ccc.archive import CheckmkTarArchive
from cmk.ccc.exceptions import MKGeneralException
from cmk.ccc.user import UserId
from cmk.gui.watolib import backup_snapshots


def _snapshot_files() -> Generator[pathlib.Path]:
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
    with CheckmkTarArchive.from_path(
        next(_snapshot_files()), streaming=False, compression="*"
    ) as snapshot_tar:
        backup_snapshots.extract_snapshot(
            snapshot_tar,
            backup_snapshots.backup_domains,
        )


@pytest.mark.skipif(os.getuid() == 0, reason="enable once CI stops running as root")
def test_extract_snapshot_permission_check_uses_real_paths(
    tmp_path: pathlib.Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(cmk.utils.paths, "var_dir", tmp_path)

    # The domain prefix is writable, but one config file inside it is read-only —
    # simulating a file owned by root (e.g. written by an operator or mounted read-only).
    prefix = tmp_path / "check_mk_prefix"
    prefix.mkdir()
    restricted = prefix / "global.mk"
    restricted.write_text("original")
    restricted.chmod(0o444)

    # A snapshot is a nested tar: the outer archive contains per-domain .tar.gz members.
    # The member name "check_mk.tar.gz" tells extract_snapshot this is the "check_mk" domain.
    inner_buf = io.BytesIO()
    with tarfile.open(fileobj=inner_buf, mode="w:gz") as inner:
        inner.add(str(restricted), arcname="./global.mk")
    inner_bytes = inner_buf.getvalue()

    outer_buf = io.BytesIO()
    with tarfile.open(fileobj=outer_buf, mode="w") as outer:
        info = tarfile.TarInfo("check_mk.tar.gz")
        info.size = len(inner_bytes)
        outer.addfile(info, io.BytesIO(inner_bytes))
    outer_bytes = outer_buf.getvalue()

    domain: backup_snapshots.DomainSpec = {
        "title": "Check_MK",
        "prefix": str(prefix),
        "paths": [("file", "global.mk")],
    }

    # extract_snapshot runs "tar tzf" on the inner archive and gets back "./global.mk\n".
    # it checks the real path prefix/./global.mk → not writable → error.
    with (
        CheckmkTarArchive.from_bytes(outer_bytes, streaming=False, compression="*") as snapshot_tar,
        pytest.raises(MKGeneralException) as exc_info,
    ):
        backup_snapshots.extract_snapshot(snapshot_tar, {"check_mk": domain})

    assert "global.mk" in str(exc_info.value)
    assert str(prefix) in str(exc_info.value)
