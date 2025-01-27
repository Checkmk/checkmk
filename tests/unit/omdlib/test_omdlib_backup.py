#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


import tarfile
from pathlib import Path

import pytest

import omdlib
import omdlib.backup
from omdlib.contexts import SiteContext


@pytest.fixture()
def site(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> SiteContext:
    monkeypatch.setattr(omdlib, "__version__", "1.3.3i7.cee")
    omd_root = tmp_path / "site"
    omd_root.mkdir(parents=True, exist_ok=True)
    (omd_root / "version").symlink_to("../versions/%s" % omdlib.__version__)

    class UnitTestSite(SiteContext):
        @property
        def dir(self):
            return str(omd_root)

    return UnitTestSite("unit")


def test_backup_site_to_tarfile(site: SiteContext, tmp_path: Path) -> None:
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


def test_backup_site_to_tarfile_broken_link(site: SiteContext, tmp_path: Path) -> None:
    Path(site.dir + "/link").symlink_to("agag")

    tar_path = tmp_path / "backup.tar"
    with tar_path.open("wb") as backup_tar:
        omdlib.backup.backup_site_to_tarfile(site, backup_tar, mode="w:", options={}, verbose=False)

    with tar_path.open("rb") as backup_tar:
        with tarfile.open(fileobj=backup_tar, mode="r:*") as tar:
            _sitename, _version = omdlib.backup.get_site_and_version_from_backup(tar)

            link = tar.getmember("unit/link")
        assert link.linkname == "agag"


def test_backup_site_to_tarfile_vanishing_files(
    site: SiteContext, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    test_dir = Path(site.dir) / "xyz"
    test_file = test_dir / "test_file"
    test_dir.mkdir(parents=True, exist_ok=True)
    test_file.touch()

    orig_gettarinfo = tarfile.TarFile.gettarinfo

    def gettarinfo(self: tarfile.TarFile, name: str, arcname: str) -> tarfile.TarInfo:
        # Remove the test_file here to simulate a vanished file during this step.
        if arcname == "unit/xyz/test_file":
            test_file.unlink()
        return orig_gettarinfo(self, name, arcname)

    monkeypatch.setattr(tarfile.TarFile, "gettarinfo", gettarinfo)

    tar_path = tmp_path / "backup.tar"
    with tar_path.open("wb") as backup_tar_w:
        omdlib.backup.backup_site_to_tarfile(
            site, backup_tar_w, mode="w:", options={}, verbose=False
        )

    assert not test_file.exists()  # check that the monkeypatch worked

    with tar_path.open("rb") as backup_tar_r:
        with tarfile.open(fileobj=backup_tar_r, mode="r:*") as tar:
            _sitename, _version = omdlib.backup.get_site_and_version_from_backup(tar)
