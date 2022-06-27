#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# pylint: disable=redefined-outer-name

import tarfile
from pathlib import Path

import pytest

import omdlib
import omdlib.backup
import omdlib.main


@pytest.fixture()
def site(tmp_path, monkeypatch):
    monkeypatch.setattr(omdlib, "__version__", "1.3.3i7.cee")
    omd_root = tmp_path / "site"
    omd_root.mkdir(parents=True, exist_ok=True)
    (omd_root / "version").symlink_to("../versions/%s" % omdlib.__version__)

    class UnitTestSite(omdlib.main.SiteContext):
        @property
        def dir(self):
            return str(omd_root)

    return UnitTestSite("unit")


def test_backup_site_to_tarfile(site, tmp_path) -> None:
    # Write some file for testing the backup procedure
    with Path(site.dir + "/test123").open("w", encoding="utf-8") as f:
        f.write("uftauftauftata")

    tar_path = tmp_path / "backup.tar"
    with tar_path.open("wb") as backup_tar:
        omdlib.backup.backup_site_to_tarfile(site, backup_tar, mode="w:", options={}, verbose=False)

    with tar_path.open("rb") as backup_tar:
        with tarfile.open(fileobj=backup_tar, mode="r:*") as tar:
            sitename, version = omdlib.backup.get_site_and_version_from_backup(tar)
            names = [tarinfo.name for tarinfo in tar]
    assert sitename == "unit"
    assert version == "1.3.3i7.cee"
    assert "unit/test123" in names


def test_backup_site_to_tarfile_broken_link(site, tmp_path) -> None:
    Path(site.dir + "/link").symlink_to("agag")

    tar_path = tmp_path / "backup.tar"
    with tar_path.open("wb") as backup_tar:
        omdlib.backup.backup_site_to_tarfile(site, backup_tar, mode="w:", options={}, verbose=False)

    with tar_path.open("rb") as backup_tar:
        with tarfile.open(fileobj=backup_tar, mode="r:*") as tar:
            _sitename, _version = omdlib.backup.get_site_and_version_from_backup(tar)

            link = tar.getmember("unit/link")
        assert link.linkname == "agag"


def test_backup_site_to_tarfile_vanishing_files(site, tmp_path, monkeypatch) -> None:
    test_dir = Path(site.dir) / "xyz"
    test_file = test_dir / "test_file"
    test_dir.mkdir(parents=True, exist_ok=True)
    test_file.touch()

    orig_add = omdlib.backup.BackupTarFile.add

    def add(
        self, name, arcname=None, recursive=True, exclude=None, filter=None
    ):  # pylint: disable=redefined-builtin
        if exclude is not None:
            raise DeprecationWarning("TarFile.add's exclude parameter should not be used")
        # The add() was called for test_dir which then calls os.listdir() and
        # add() for all found entries. Remove the test_file here to simulate
        # a vanished file during this step.
        if arcname == "unit/xyz/test_file":
            test_file.unlink()
        orig_add(self, name, arcname, recursive, filter=filter)

    monkeypatch.setattr(omdlib.backup.BackupTarFile, "add", add)

    tar_path = tmp_path / "backup.tar"
    with tar_path.open("wb") as backup_tar:
        omdlib.backup.backup_site_to_tarfile(site, backup_tar, mode="w:", options={}, verbose=False)

    with tar_path.open("rb") as backup_tar:
        with tarfile.open(fileobj=backup_tar, mode="r:*") as tar:
            _sitename, _version = omdlib.backup.get_site_and_version_from_backup(tar)
